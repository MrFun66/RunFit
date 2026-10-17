"""跑步数据解析器。

支持：
- TCX  (WorkOutDoors / Garmin / Apple 导出)
- GPX  (含心率/步频 extension)
- Apple 健康 export.xml  (全量历史，两遍流式解析，低内存)
- CSV  (WorkOutDoors / Strava 批量导出)
"""
from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lxml import etree

# --------------------------------------------------------------------------
# 数据结构
# --------------------------------------------------------------------------


@dataclass
class Sample:
    t: float          # 相对开始秒数
    hr: float | None = None
    cadence: float | None = None
    speed: float | None = None   # m/s
    elev: float | None = None
    dist: float | None = None    # 累计米


@dataclass
class ParsedRun:
    start_time: datetime
    activity_type: str = "running"
    name: str | None = None
    distance_m: float = 0.0
    duration_s: float = 0.0
    moving_s: float | None = None
    avg_hr: float | None = None
    max_hr: float | None = None
    avg_cadence: float | None = None
    elevation_gain_m: float | None = None
    calories: float | None = None
    avg_power: float | None = None
    source: str = "unknown"
    external_id: str | None = None
    samples: list[Sample] = field(default_factory=list)
    splits: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def finalize(self) -> "ParsedRun":
        """补齐派生字段。"""
        s = self.samples
        if s and not self.duration_s:
            self.duration_s = s[-1].t

        hrs = [x.hr for x in s if x.hr and x.hr > 30]
        if hrs and not self.avg_hr:
            self.avg_hr = round(sum(hrs) / len(hrs), 1)
        if hrs and not self.max_hr:
            self.max_hr = round(max(hrs), 1)

        cads = [x.cadence for x in s if x.cadence and x.cadence > 0]
        if cads and not self.avg_cadence:
            self.avg_cadence = round(sum(cads) / len(cads), 1)

        if s and not self.distance_m:
            ds = [x.dist for x in s if x.dist is not None]
            self.distance_m = ds[-1] if ds else 0.0

        if self.elevation_gain_m is None:
            self.elevation_gain_m = _elevation_gain(s)

        if not self.moving_s:
            self.moving_s = _moving_time(s)

        if not self.splits:
            self.splits = compute_splits(s, self.distance_m)

        if self.avg_power is None:
            ps = []
            for x in s:
                p = getattr(x, "power", None)
                if p:
                    ps.append(p)
            if ps:
                self.avg_power = round(sum(ps) / len(ps), 1)
        return self


def _elevation_gain(samples: list[Sample], threshold: float = 1.0) -> float:
    gain, last = 0.0, None
    for s in samples:
        if s.elev is None:
            continue
        if last is not None and s.elev - last > threshold:
            gain += s.elev - last
        if last is None or abs(s.elev - last) > 0.2:
            last = s.elev
    return round(gain, 1)


def _moving_time(samples: list[Sample], min_speed: float = 0.5) -> float | None:
    """粗略移动时间：速度低于阈值且连续 10s 以上视为停止。"""
    if len(samples) < 3:
        return None
    moving = 0.0
    stop_run = 0.0
    for i in range(1, len(samples)):
        dt = samples[i].t - samples[i - 1].t
        if dt <= 0 or dt > 60:
            continue
        v = samples[i].speed
        if v is None:
            moving += dt
            continue
        if v < min_speed:
            stop_run += dt
        else:
            if stop_run < 10:
                moving += stop_run
            stop_run = 0.0
            moving += dt
    return round(moving, 1)


def compute_splits(samples: list[Sample], total_dist: float) -> list[dict]:
    """按公里切分。"""
    splits: list[dict] = []
    if not samples or total_dist <= 0:
        return splits

    km = 1
    seg_start_t = samples[0].t
    seg_hrs: list[float] = []
    seg_cads: list[float] = []
    seg_elev_gain = 0.0
    last_elev = None

    for s in samples:
        if s.hr:
            seg_hrs.append(s.hr)
        if s.cadence:
            seg_cads.append(s.cadence)
        if s.elev is not None:
            if last_elev is not None and s.elev - last_elev > 1.0:
                seg_elev_gain += s.elev - last_elev
            last_elev = s.elev

        d = s.dist if s.dist is not None else 0.0
        if d >= km * 1000 - 1e-6:
            dur = s.t - seg_start_t
            splits.append(
                {
                    "km": km,
                    "duration_s": round(dur, 1),
                    "pace_s_per_km": round(dur, 1) if dur > 0 else None,
                    "avg_hr": round(sum(seg_hrs) / len(seg_hrs), 1) if seg_hrs else None,
                    "avg_cadence": round(sum(seg_cads) / len(seg_cads), 1) if seg_cads else None,
                    "elev_gain_m": round(seg_elev_gain, 1),
                }
            )
            km += 1
            seg_start_t = s.t
            seg_hrs, seg_cads, seg_elev_gain, last_elev = [], [], 0.0, None

    # 最后不足 1km 的尾段
    if samples:
        done = (km - 1) * 1000
        rest = total_dist - done
        if rest > 50:
            dur = samples[-1].t - seg_start_t
            splits.append(
                {
                    "km": km,
                    "duration_s": round(dur, 1),
                    "pace_s_per_km": round(dur / (rest / 1000), 1) if rest > 0 else None,
                    "avg_hr": round(sum(seg_hrs) / len(seg_hrs), 1) if seg_hrs else None,
                    "avg_cadence": round(sum(seg_cads) / len(seg_cads), 1) if seg_cads else None,
                    "elev_gain_m": round(seg_elev_gain, 1),
                    "partial": True,
                }
            )
    return splits


def downsample(samples: list[Sample], max_points: int = 600) -> list[Sample]:
    if len(samples) <= max_points:
        return samples
    step = len(samples) / max_points
    return [samples[min(int(i * step), len(samples) - 1)] for i in range(max_points)]


# --------------------------------------------------------------------------
# 工具函数
# --------------------------------------------------------------------------


def _text(el, path: str) -> str | None:
    r = el.find(path)
    return r.text.strip() if r is not None and r.text else None


def _num(el, path: str) -> float | None:
    t = _text(el, path)
    if t is None:
        return None
    try:
        return float(t)
    except ValueError:
        return None


_ISO_RE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?"
)


def parse_dt(text: str | None) -> datetime | None:
    if not text:
        return None
    m = _ISO_RE.match(text.strip())
    if not m:
        return None
    y, mo, d, hh, mm, ss, frac, tz = m.groups()
    micro = int(float(frac) * 1_000_000) if frac else 0
    dt = datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss), micro)
    if tz and tz != "Z":
        sign = 1 if tz[0] == "+" else -1
        tzt = tz[1:].replace(":", "")
        dt -= sign * timedelta(hours=int(tzt[:2]), minutes=int(tzt[2:]))
    return dt


# --------------------------------------------------------------------------
# TCX
# --------------------------------------------------------------------------


def parse_tcx(data: bytes | str, source: str = "tcx") -> ParsedRun:
    if isinstance(data, str):
        data = data.encode("utf-8")
    root = etree.fromstring(data, parser=etree.XMLParser(recover=True, huge_tree=True))

    # 抹掉标签上的命名空间：Garmin / Apple / WorkOutDoors 用的 URI 各不相同，
    # 而 find() 在不传 namespaces 时会因为缺 prefix map 抛 "prefix not found"。
    # 统一转成裸标签名后，后面所有 p() 都退化为恒等映射。
    for el in root.iter():
        tag = el.tag
        if isinstance(tag, str) and tag.startswith("{"):
            el.tag = tag.split("}", 1)[1]
    etree.cleanup_namespaces(root)

    ns = root.nsmap.get(None, "")
    nsd = {"t": ns} if ns else {}
    # 用 Clark notation（{uri}tag）而不是 t: 前缀：
    # ElementPath 解析带前缀的路径时必须额外传 namespaces=，否则报
    # "prefix 't' not found in prefix map"。Clark 形式无需该参数。
    p = (lambda k: f"{{{ns}}}{k}") if ns else (lambda k: k)

    act = root.find(f".//{p('Activities')}/{p('Activity')}")
    if act is None:
        act = root.find(f".//{p('Activity')}")
    if act is None:
        raise ValueError("TCX 中没有 Activity 节点")

    sport = (act.get("Sport") or "Running").lower()
    lap_nodes = act.findall(f".//{p('Lap')}") or act.findall(f"{p('Lap')}")

    start = None
    for lap in lap_nodes:
        id_node = lap.find(p("Id")) if False else None
        st = _text(lap, p("StartTime")) if False else None
        # StartTime 是属性
        st = lap.get("StartTime")
        if st:
            start = parse_dt(st)
            if start:
                break
    if start is None:
        st = root.get("StartTime")
        start = parse_dt(st)
    if start is None:
        first_tp = root.find(f".//{p('Trackpoint')}")
        if first_tp is not None:
            start = parse_dt(_text(first_tp, p("Time")))
    if start is None:
        raise ValueError("TCX 缺少开始时间")

    samples: list[Sample] = []
    total_dist = 0.0
    total_time = 0.0
    calories = None

    for lap in lap_nodes:
        d = _num(lap, p("DistanceMeters"))
        if d:
            total_dist = max(total_dist, d)
        tt = _num(lap, p("TotalTimeSeconds"))
        if tt:
            total_time += tt
        cal = _num(lap, p("Calories"))
        if cal:
            calories = (calories or 0) + cal

        for tp in lap.findall(f".//{p('Trackpoint')}"):
            t = parse_dt(_text(tp, p("Time")))
            if t is None:
                continue
            rel = (t - start).total_seconds()
            if rel < 0:
                continue
            hr = _num(tp, f"{p('HeartRateBpm')}/{p('Value')}")
            cad = _num(tp, p("Cadence"))
            dist = _num(tp, p("DistanceMeters"))
            elev = _num(tp, p("AltitudeMeters"))
            speed = None
            for ext in tp.findall(f"{p('Extensions')}/*"):
                local = etree.QName(ext).localname.lower()
                if "speed" in local:
                    try:
                        speed = float(ext.text)
                    except (TypeError, ValueError):
                        pass
                elif "cadence" in local:
                    try:
                        cad = float(ext.text)
                    except (TypeError, ValueError):
                        pass
                elif "watts" in local or local == "power":
                    try:
                        val = float(ext.text)
                    except (TypeError, ValueError):
                        val = None
                    if val is not None:
                        samples.append(Sample(t=rel))  # placeholder replaced below
                        samples.pop()
            samples.append(
                Sample(t=rel, hr=hr, cadence=cad, speed=speed, elev=elev, dist=dist)
            )

    samples.sort(key=lambda x: x.t)
    # 去重（同一时间点）
    dedup: list[Sample] = []
    for s in samples:
        if dedup and abs(s.t - dedup[-1].t) < 0.5:
            dedup[-1] = s
        else:
            dedup.append(s)
    samples = dedup

    # 补 speed（缺失时用距离差推算）
    for i, s in enumerate(samples):
        if s.speed is None and i > 0:
            prev = samples[i - 1]
            dt = s.t - prev.t
            if dt > 0 and s.dist is not None and prev.dist is not None:
                s.speed = max(0.0, (s.dist - prev.dist) / dt)
        if s.dist is None and i > 0:
            pass

    run = ParsedRun(
        start_time=start,
        activity_type=_map_sport(sport),
        distance_m=total_dist,
        duration_s=total_time or (samples[-1].t if samples else 0.0),
        calories=calories,
        source=source,
        samples=samples,
        external_id=f"tcx:{start.isoformat()}",
    )
    run.meta["sport"] = sport
    return run.finalize()


def _map_sport(sport: str) -> str:
    s = sport.lower()
    if "run" in s or "jog" in s:
        return "running"
    if "bike" in s or "cycl" in s:
        return "cycling"
    if "walk" in s or "hike" in s:
        return "walking"
    if "swim" in s:
        return "swimming"
    return s or "running"


# --------------------------------------------------------------------------
# GPX
# --------------------------------------------------------------------------


def parse_gpx(data: bytes | str, source: str = "gpx") -> ParsedRun:
    if isinstance(data, str):
        data = data.encode("utf-8")
    root = etree.fromstring(data, parser=etree.XMLParser(recover=True, huge_tree=True))

    trkpts = root.findall(".//{*}trkpt")
    if not trkpts:
        raise ValueError("GPX 中没有 trkpt")

    samples: list[Sample] = []
    start = None
    dist = 0.0
    prev_lat = prev_lon = None

    for pt in trkpts:
        lat, lon = pt.get("lat"), pt.get("lon")
        t = parse_dt(_text(pt, "{*}time"))
        if t and start is None:
            start = t
        if start is None or t is None:
            continue
        rel = (t - start).total_seconds()
        if rel < 0:
            continue

        elev = _num(pt, "{*}ele")
        hr = cad = None
        for ext in pt.iter():
            local = etree.QName(ext).localname.lower() if isinstance(ext.tag, str) else ""
            if local in ("hr", "heartratebpm", "value") and ext.text:
                try:
                    v = float(ext.text)
                    if 30 < v < 250:
                        hr = v
                except ValueError:
                    pass
            elif local in ("cad", "cadence") and ext.text:
                try:
                    cad = float(ext.text)
                except ValueError:
                    pass

        if lat and lon:
            flat, flon = float(lat), float(lon)
            if prev_lat is not None:
                dist += _haversine(prev_lat, prev_lon, flat, flon)
            prev_lat, prev_lon = flat, flon

        samples.append(
            Sample(t=rel, hr=hr, cadence=cad, elev=elev, dist=dist if dist else None)
        )

    if start is None:
        raise ValueError("GPX 缺少时间戳")

    run = ParsedRun(
        start_time=start,
        distance_m=dist,
        duration_s=samples[-1].t if samples else 0.0,
        source=source,
        samples=samples,
        external_id=f"gpx:{start.isoformat()}",
    )
    return run.finalize()


def _haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------
# Apple 健康 export.xml
# --------------------------------------------------------------------------

_APPLE_RUN_TYPES = {
    "HKWorkoutActivityTypeRunning",
    "HKWorkoutActivityTypeWalking",
    "HKWorkoutActivityTypeCycling",
    "HKWorkoutActivityTypeHiking",
    "HKWorkoutActivityTypeSwimming",
    "HKWorkoutActivityTypeTraditionalStrengthTraining",
    "HKWorkoutActivityTypeFunctionalStrengthTraining",
    "HKWorkoutActivityTypeHighIntensityIntervalTraining",
    "HKWorkoutActivityTypeYoga",
    "HKWorkoutActivityTypeElliptical",
    "HKWorkoutActivityTypeRowing",
}

_APPLE_TYPE_MAP = {
    "HKWorkoutActivityTypeRunning": "running",
    "HKWorkoutActivityTypeWalking": "walking",
    "HKWorkoutActivityTypeCycling": "cycling",
    "HKWorkoutActivityTypeHiking": "hiking",
    "HKWorkoutActivityTypeSwimming": "swimming",
    "HKWorkoutActivityTypeTraditionalStrengthTraining": "strength",
    "HKWorkoutActivityTypeFunctionalStrengthTraining": "strength",
    "HKWorkoutActivityTypeHighIntensityIntervalTraining": "hiit",
    "HKWorkoutActivityTypeYoga": "yoga",
    "HKWorkoutActivityTypeElliptical": "elliptical",
    "HKWorkoutActivityTypeRowing": "rowing",
}


def iter_apple_workouts(path: Path):
    """第一遍：只取 Workout 节点，内存恒定。"""
    ctx = etree.iterparse(str(path), events=("end",), tag="Workout", huge_tree=True, recover=True)
    for _, el in ctx:
        try:
            yield _apple_workout_from_el(el)
        finally:
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]


def _apple_workout_from_el(el) -> dict:
    atype = el.get("workoutActivityType") or ""
    start = parse_dt(el.get("startDate"))
    end = parse_dt(el.get("endDate"))
    dur = el.get("duration")
    unit = (el.get("durationUnit") or "min").lower()
    try:
        dur = float(dur) if dur else None
    except ValueError:
        dur = None
    if dur is not None:
        if unit.startswith("min"):
            dur *= 60
        elif unit.startswith("h"):
            dur *= 3600
        elif unit.startswith("s"):
            pass
        else:
            dur *= 60

    total_dist = None
    for attr in ("totalDistance", "totalDistanceUnit"):
        pass
    td = el.get("totalDistance")
    tdu = (el.get("totalDistanceUnit") or "km").lower()
    if td:
        try:
            total_dist = float(td)
            if tdu in ("km",):
                total_dist *= 1000
            elif tdu in ("mi",):
                total_dist *= 1609.344
            elif tdu in ("m",):
                pass
            else:
                total_dist *= 1000
        except ValueError:
            total_dist = None

    stats = {}
    for st in el.findall("WorkoutStatistics"):
        t = st.get("type") or ""
        try:
            avg = float(st.get("average")) if st.get("average") else None
            mx = float(st.get("maximum")) if st.get("maximum") else None
            sm = float(st.get("sum")) if st.get("sum") else None
        except ValueError:
            continue
        stats[t] = {"avg": avg, "max": mx, "sum": sm}

    return {
        "activity_type": _APPLE_TYPE_MAP.get(atype, atype.replace("HKWorkoutActivityType", "").lower()),
        "apple_type": atype,
        "start": start,
        "end": end,
        "duration_s": dur,
        "distance_m": total_dist,
        "energy_kcal": stats.get("HKQuantityTypeIdentifierActiveEnergyBurned", {}).get("sum"),
        "avg_hr": stats.get("HKQuantityTypeIdentifierHeartRate", {}).get("avg"),
        "max_hr": stats.get("HKQuantityTypeIdentifierHeartRate", {}).get("max"),
        "avg_cadence": stats.get("HKQuantityTypeIdentifierStepCount", {}).get("avg"),
    }


def iter_apple_health_records(path: Path, wanted: set[str]):
    """第二遍：流式提取指定 Record 类型。"""
    ctx = etree.iterparse(
        str(path), events=("end",), tag="Record", huge_tree=True, recover=True
    )
    for _, el in ctx:
        t = el.get("type") or ""
        if t in wanted:
            try:
                val = float(el.get("value") or "nan")
            except ValueError:
                val = None
            if val is not None and not math.isnan(val):
                yield t, parse_dt(el.get("startDate")), val
        el.clear()
        while el.getprevious() is not None:
            del el.getparent()[0]


def parse_apple_export(path: Path, progress=None) -> dict:
    """解析 Apple 健康 export.xml。

    返回 {"workouts": [...], "body_metrics": [...], "hr_samples": [...]}
    """
    path = Path(path)
    workouts = []
    for w in iter_apple_workouts(path):
        if w["start"] and w["duration_s"]:
            workouts.append(w)
        if progress and len(workouts) % 50 == 0:
            progress(f"已读取 {len(workouts)} 条训练")

    wanted = {
        "HKQuantityTypeIdentifierBodyMass",
        "HKQuantityTypeIdentifierBodyFatPercentage",
        "HKQuantityTypeIdentifierRestingHeartRate",
        "HKQuantityTypeIdentifierHeartRate",
        "HKQuantityTypeIdentifierStepCount",
        "HKQuantityTypeIdentifierAppleExerciseTime",
    }
    body: dict[str, dict] = {}
    hr_samples: list[tuple[datetime, float]] = []
    for t, dt, val in iter_apple_health_records(path, wanted):
        if dt is None:
            continue
        day = dt.date().isoformat()
        if t == "HKQuantityTypeIdentifierBodyMass":
            body.setdefault(day, {})["weight_kg"] = val
        elif t == "HKQuantityTypeIdentifierBodyFatPercentage":
            v = val * 100 if val <= 1.5 else val
            body.setdefault(day, {})["bodyfat_pct"] = round(v, 1)
        elif t == "HKQuantityTypeIdentifierRestingHeartRate":
            body.setdefault(day, {})["resting_hr"] = val
        elif t == "HKQuantityTypeIdentifierHeartRate":
            hr_samples.append((dt, val))

    return {"workouts": workouts, "body_metrics": body, "hr_samples": hr_samples}


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------

_CSV_ALIASES = {
    "start": ["start time", "starttime", "date", "start_date", "activity date", "time", "开始时间", "日期"],
    "distance": ["distance", "distance (m)", "dist", "distance_m", "距离"],
    "distance_km": ["distance (km)", "distance_km", "公里"],
    "duration": ["duration", "moving time", "elapsed time", "time (s)", "时长"],
    "duration_s": ["duration (s)", "duration_s", "seconds"],
    "duration_hms": ["duration", "elapsed time", "moving time"],
    "avg_hr": ["avg hr", "average heart rate", "avg_heart_rate", "平均心率"],
    "max_hr": ["max hr", "maximum heart rate", "max_heart_rate", "最大心率"],
    "cadence": ["avg run cadence", "cadence", "avg cadence", "步频"],
    "elev": ["elevation gain", "total ascent", "elev_gain", "爬升"],
    "calories": ["calories", "energy", "卡路里"],
    "name": ["activity name", "title", "name", "名称"],
    "type": ["activity type", "type", "sport", "类型"],
}


def _hms_to_s(v: str) -> float | None:
    if not v:
        return None
    v = v.strip()
    if ":" in v:
        parts = v.split(":")
        try:
            nums = [float(x) for x in parts]
        except ValueError:
            return None
        if len(nums) == 3:
            return nums[0] * 3600 + nums[1] * 60 + nums[2]
        if len(nums) == 2:
            return nums[0] * 60 + nums[1]
    try:
        return float(v)
    except ValueError:
        return None


def parse_csv(text: str, source: str = "csv") -> list[ParsedRun]:
    """解析多行汇总 CSV（WorkOutDoors / Strava 导出）。"""
    # 自动探测分隔符
    sample = text[:4096]
    delim = ","
    for cand in (",", ";", "\t"):
        if sample.count(cand) > sample.count(delim):
            delim = cand

    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    if not reader.fieldnames:
        raise ValueError("CSV 没有表头")

    cols = {f.strip().lower(): f for f in reader.fieldnames}

    def pick(key: str) -> str | None:
        for alias in _CSV_ALIASES.get(key, []):
            if alias in cols:
                return cols[alias]
        return None

    c_start = pick("start")
    if not c_start:
        raise ValueError("CSV 缺少开始时间列")

    c_dist = pick("distance")
    c_distkm = pick("distance_km")
    c_dur = pick("duration_s") or pick("duration") or pick("duration_hms")
    c_ahr = pick("avg_hr")
    c_mhr = pick("max_hr")
    c_cad = pick("cadence")
    c_elev = pick("elev")
    c_cal = pick("calories")
    c_name = pick("name")
    c_type = pick("type")

    runs: list[ParsedRun] = []
    for row in reader:
        start = parse_dt(row.get(c_start, ""))
        if start is None:
            # 尝试常见格式
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%d/%m/%Y %H:%M"):
                try:
                    start = datetime.strptime(row.get(c_start, "").strip(), fmt)
                    break
                except ValueError:
                    continue
        if start is None:
            continue

        dist = None
        if c_dist:
            try:
                dist = float(row.get(c_dist) or 0)
            except ValueError:
                dist = None
        if (dist is None or dist == 0) and c_distkm:
            try:
                dist = float(row.get(c_distkm) or 0) * 1000
            except ValueError:
                pass

        dur = _hms_to_s(row.get(c_dur) or "") if c_dur else None

        def fnum(col):
            if not col:
                return None
            try:
                v = float(row.get(col) or "")
                return v if v > 0 else None
            except (TypeError, ValueError):
                return None

        r = ParsedRun(
            start_time=start,
            activity_type="running",
            name=(row.get(c_name) or "").strip() or None if c_name else None,
            distance_m=dist or 0.0,
            duration_s=dur or 0.0,
            avg_hr=fnum(c_ahr),
            max_hr=fnum(c_mhr),
            avg_cadence=fnum(c_cad),
            elevation_gain_m=fnum(c_elev),
            calories=fnum(c_cal),
            source=source,
            external_id=f"csv:{start.isoformat()}",
        )
        if c_type:
            r.activity_type = _map_sport(row.get(c_type) or "running")
        runs.append(r.finalize())

    return runs


# --------------------------------------------------------------------------
# 统一入口
# --------------------------------------------------------------------------


def parse_file(path: Path) -> list[ParsedRun]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".tcx":
        return [parse_tcx(path.read_bytes(), source="tcx")]
    if suffix == ".gpx":
        return [parse_gpx(path.read_bytes(), source="gpx")]
    if suffix == ".csv":
        raw = path.read_bytes()
        for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
            try:
                return parse_csv(raw.decode(enc), source="csv")
            except UnicodeDecodeError:
                continue
        raise ValueError("CSV 编码无法识别")
    if suffix == ".xml":
        raise ValueError("Apple export.xml 请使用专用导入接口 /api/import/apple")
    raise ValueError(f"不支持的文件类型: {suffix}")