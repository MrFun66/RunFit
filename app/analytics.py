"""跑步与训练负荷分析。"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta

# --------------------------------------------------------------------------
# 心率区间（基于最大心率储备 HRR / Karvonen）
# --------------------------------------------------------------------------
HR_ZONES = [
    ("Z1 恢复", 0.50, 0.60),
    ("Z2 有氧", 0.60, 0.70),
    ("Z3 节奏", 0.70, 0.80),
    ("Z4 阈值", 0.80, 0.90),
    ("Z5 无氧", 0.90, 1.00),
]

ZONE_WEIGHT = [1.0, 2.0, 3.0, 4.0, 5.0]


def max_hr_estimate(age: int | None, observed: float | None = None) -> float:
    """Tanaka 公式，若有实测最大值优先用实测。"""
    est = 208 - 0.7 * age if age else 190.0
    if observed and observed > est:
        return float(observed)
    return float(est)


def hr_zones(hr_max: float, hr_rest: float = 60.0) -> list[dict]:
    out = []
    for name, lo, hi in HR_ZONES:
        out.append(
            {
                "name": name,
                "low": round(hr_rest + (hr_max - hr_rest) * lo),
                "high": round(hr_rest + (hr_max - hr_rest) * hi),
            }
        )
    return out


def zone_of(hr: float, hr_max: float, hr_rest: float = 60.0) -> int:
    """返回 0-4 的区间索引。"""
    if hr_max <= hr_rest:
        return 0
    pct = (hr - hr_rest) / (hr_max - hr_rest)
    for i, (_, lo, hi) in enumerate(HR_ZONES):
        if pct < hi:
            return i
    return 4


def trimp(duration_min: float, avg_hr: float, hr_max: float, hr_rest: float = 60.0, sex: str = "male") -> float:
    """Banister TRIMP。"""
    if hr_max <= hr_rest:
        return 0.0
    hrr = max(0.0, min(1.0, (avg_hr - hr_rest) / (hr_max - hr_rest)))
    b = 1.92 if sex == "male" else 1.67
    return duration_min * hrr * 0.64 * math.exp(b * hrr)


def run_load(run: dict, hr_max: float, hr_rest: float = 60.0, sex: str = "male") -> float:
    """单次跑步训练负荷。无心率时用配速等效估算。"""
    dur = (run.get("moving_s") or run.get("duration_s") or 0) / 60.0
    if dur <= 0:
        return 0.0
    avg_hr = run.get("avg_hr")
    if avg_hr:
        return round(trimp(dur, avg_hr, hr_max, hr_rest, sex), 1)
    # 兜底：按配速估算强度（5:00/km ≈ 0.75 HRR）
    dist_km = (run.get("distance_m") or 0) / 1000.0
    pace = dur / dist_km if dist_km > 0 else 6.0
    hrr = max(0.4, min(0.95, 1.15 - pace / 8.0))
    b = 1.92 if sex == "male" else 1.67
    return round(dur * hrr * 0.64 * math.exp(b * hrr), 1)


def acute_chronic_ratio(daily_loads: list[tuple[date, float]], today: date | None = None) -> dict:
    """ACWR：7 天急性负荷 / 28 天慢性负荷。"""
    today = today or date.today()
    acute = sum(v for d, v in daily_loads if (today - d).days < 7)
    chronic = sum(v for d, v in daily_loads if (today - d).days < 28) / 4.0
    ratio = (acute / chronic) if chronic > 0 else 0.0
    if chronic == 0:
        flag, advice = "无基线", "刚开始，先积累 2-3 周基础负荷"
    elif ratio < 0.8:
        flag, advice = "负荷偏低", "可以适度加量，每周增幅不超过 10%"
    elif ratio <= 1.3:
        flag, advice = "理想区间", "负荷递增合理，继续保持"
    elif ratio <= 1.5:
        flag, advice = "偏高", "接近警戒线，本周不要再加量"
    else:
        flag, advice = "过高", "受伤风险显著上升，建议减量或安排恢复周"
    return {
        "acute": round(acute, 1),
        "chronic_weekly": round(chronic, 1),
        "ratio": round(ratio, 2),
        "flag": flag,
        "advice": advice,
    }


def aerobic_decoupling(samples: list[dict]) -> float | None:
    """有氧解耦：前后半程 配速/心率 比值漂移百分比。"""
    pts = [s for s in samples if s.get("hr") and s.get("speed") and s["speed"] > 0.5]
    if len(pts) < 40:
        return None
    half = len(pts) // 2
    def ratio(seg):
        hrs = [p["hr"] for p in seg]
        sps = [p["speed"] for p in seg]
        return (sum(hrs) / len(hrs)) / (sum(sps) / len(sps))
    r1, r2 = ratio(pts[:half]), ratio(pts[half:])
    if r1 <= 0:
        return None
    return round((r2 - r1) / r1 * 100, 2)


def pace_str(distance_m: float | None, duration_s: float | None) -> str:
    if not distance_m or not duration_s or distance_m <= 0:
        return "-"
    sec_per_km = duration_s / (distance_m / 1000.0)
    return f"{int(sec_per_km // 60)}:{int(sec_per_km % 60):02d}"


def fmt_duration(seconds: float | None) -> str:
    if not seconds:
        return "-"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def analyze_run(run: dict, hr_max: float, hr_rest: float = 60.0) -> dict:
    """单次跑步详细分析。"""
    samples = []
    if run.get("samples_json"):
        try:
            samples = json.loads(run["samples_json"])
        except (json.JSONDecodeError, TypeError):
            samples = []

    zone_time = [0.0] * 5
    for i in range(1, len(samples)):
        prev, cur = samples[i - 1], samples[i]
        dt = (cur.get("t", 0) or 0) - (prev.get("t", 0) or 0)
        hr = cur.get("hr")
        if hr and 0 < dt < 300:
            zone_time[zone_of(hr, hr_max, hr_rest)] += dt

    total = sum(zone_time) or 1.0
    zone_pct = [round(z / total * 100, 1) for z in zone_time]

    dist_km = (run.get("distance_m") or 0) / 1000.0
    dur = run.get("duration_s") or 0
    return {
        "pace": pace_str(run.get("distance_m"), run.get("moving_s") or dur),
        "distance_km": round(dist_km, 2),
        "duration": fmt_duration(dur),
        "avg_hr": run.get("avg_hr"),
        "max_hr": run.get("max_hr"),
        "cadence": run.get("avg_cadence"),
        "elevation_gain": run.get("elevation_gain_m"),
        "zone_time_min": [round(z / 60, 1) for z in zone_time],
        "zone_pct": zone_pct,
        "decoupling_pct": aerobic_decoupling(samples),
        "splits": json.loads(run["splits_json"]) if run.get("splits_json") else [],
        "load": run_load(run, hr_max, hr_rest),
    }


def weekly_summary(runs: list[dict], hr_max: float, hr_rest: float = 60.0) -> dict:
    """按 ISO 周聚合。"""
    buckets: dict[str, dict] = {}
    for r in runs:
        st = r.get("start_time")
        if isinstance(st, str):
            st = datetime.fromisoformat(st)
        if not st:
            continue
        y, w, _ = st.isocalendar()
        key = f"{y}-W{w:02d}"
        b = buckets.setdefault(key, {"week": key, "runs": 0, "km": 0.0, "sec": 0.0, "load": 0.0, "hr_sum": 0.0, "hr_n": 0})
        b["runs"] += 1
        b["km"] += (r.get("distance_m") or 0) / 1000.0
        b["sec"] += r.get("duration_s") or 0
        b["load"] += run_load(r, hr_max, hr_rest)
        if r.get("avg_hr"):
            b["hr_sum"] += r["avg_hr"]
            b["hr_n"] += 1

    out = []
    for b in sorted(buckets.values(), key=lambda x: x["week"]):
        out.append(
            {
                "week": b["week"],
                "runs": b["runs"],
                "km": round(b["km"], 2),
                "duration": fmt_duration(b["sec"]),
                "avg_pace": pace_str(b["km"] * 1000, b["sec"]),
                "avg_hr": round(b["hr_sum"] / b["hr_n"], 1) if b["hr_n"] else None,
                "load": round(b["load"], 1),
            }
        )
    return {"weeks": out, "total_km": round(sum(b["km"] for b in buckets.values()), 2)}