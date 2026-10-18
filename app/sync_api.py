"""自动同步接口：接收 iOS「健康」/「Health Auto Export」/「快捷指令」/ Android Health Connect 推送的数据。

鉴权方式与网页登录不同：使用长期有效的 sync_token（Bearer），
方便第三方 App 保存一个固定 URL + Token 后定时 POST，无需处理 Cookie 过期。
"""
from __future__ import annotations

import json
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from . import parsers
from .db import get_db
from .config import settings
from .models import BodyMetric, HealthSample, Run, User

router = APIRouter(prefix="/api/sync", tags=["sync"])

CN_TZ = timezone(timedelta(hours=8))


# --------------------------------------------------------------------------
# 令牌
# --------------------------------------------------------------------------
def ensure_sync_token(db: OrmSession, user: User) -> str:
    if not user.sync_token:
        user.sync_token = secrets.token_urlsafe(32)
        db.commit()
    return user.sync_token


def _user_by_token(db: OrmSession, token: str) -> User:
    if not token:
        raise HTTPException(401, "缺少同步令牌")
    user = db.scalars(select(User).where(User.sync_token == token)).first()
    if not user:
        raise HTTPException(401, "同步令牌无效，请在「我的 → 设置」重新获取")
    return user


# --------------------------------------------------------------------------
# 令牌管理（网页登录态调用）
# --------------------------------------------------------------------------
@router.get("/token")
def get_sync_token(request: Request, db: OrmSession = Depends(get_db)):
    from .security import current_user

    user = current_user(request, db)
    token = ensure_sync_token(db, user)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "127.0.0.1:7788"
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    return {
        "ok": True,
        "token": token,
        "endpoint": f"{proto}://{host}/api/sync/health",
        "examples": {
            "curl": (
                f"curl -X POST '{proto}://{host}/api/sync/health' "
                f"-H 'Authorization: Bearer {token}' "
                "-H 'Content-Type: application/json' "
                "-d '{\"date\":\"%s\",\"metrics\":{\"weight_kg\":74.2,\"bodyfat_pct\":18.5,"
                "\"resting_hr\":57,\"sleep_hours\":8}}'" % date.today().isoformat()
            )
        },
    }


@router.post("/token/rotate")
def rotate_sync_token(request: Request, db: OrmSession = Depends(get_db)):
    from .security import current_user

    user = current_user(request, db)
    user.sync_token = secrets.token_urlsafe(32)
    db.commit()
    return {"ok": True, "token": user.sync_token, "message": "旧令牌已失效，请在手机端更新"}


def _touch_last_sync(db: OrmSession, user: User, summary: dict) -> None:
    """记录最近一次同步时间与结果，供网页端展示「同步正常」。"""
    from .models import AppSetting
    import json as _json

    key = "last_sync_%d" % user.id
    row = db.get(AppSetting, key)
    payload = _json.dumps(
        {
            "at": datetime.now(CN_TZ).isoformat(timespec="seconds"),
            **summary,
        },
        ensure_ascii=False,
    )
    if row is None:
        db.add(AppSetting(key=key, value=payload))
    else:
        row.value = payload


# --------------------------------------------------------------------------
# 数据接收
# --------------------------------------------------------------------------
def _parse_dt(raw) -> datetime | None:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    s = str(raw).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            return dt
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _qty(obj) -> float | None:
    """Health Auto Export 的字段可能是 {"qty": 1, "units": "kg"} 或直接数字。"""
    if obj is None:
        return None
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, dict):
        for k in ("qty", "value", "sum", "avg"):
            if obj.get(k) is not None:
                try:
                    return float(obj[k])
                except (TypeError, ValueError):
                    return None
    try:
        return float(obj)
    except (TypeError, ValueError):
        return None


# Health Auto Export 指标名 -> 我们的字段
_METRIC_MAP = {
    # 体重 / 体成分
    "weight_body_mass": "weight_kg",
    "body_mass": "weight_kg",
    "weight": "weight_kg",
    "body_fat_percentage": "bodyfat_pct",
    "body_fat": "bodyfat_pct",
    "bodyfat": "bodyfat_pct",
    "lean_body_mass": "muscle_kg",
    "waist_circumference": "waist_cm",
    # 心率
    "resting_heart_rate": "resting_hr",
    "resting_hr": "resting_hr",
    # 睡眠
    "sleep_analysis": "sleep_hours",
    "sleep": "sleep_hours",
    "sleep_hours": "sleep_hours",
}


def _save_sample(db: OrmSession, user: User, day, metric: str, value: float, unit=None) -> None:
    """把任意指标存进 health_samples（同一天同指标更新，不重复插入）。"""
    row = db.scalars(
        select(HealthSample).where(
            HealthSample.user_id == user.id,
            HealthSample.date == day,
            HealthSample.metric == metric,
        )
    ).first()
    if row is None:
        row = HealthSample(user_id=user.id, date=day, metric=metric, value=float(value),
                           unit=str(unit) if unit else None, source="auto-sync")
        db.add(row)
        db.flush()
    else:
        row.value = float(value)
        if unit:
            row.unit = str(unit)


def _upsert_body(db: OrmSession, user: User, day: date, vals: dict) -> str:
    """按天 upsert 身体指标。

    注意：同一份 payload 里同一天可能有多条指标（体重、体脂、睡眠各一条），
    新建行后必须 flush，否则下一次 select 查不到，会重复 INSERT 撞唯一约束。
    """
    row = db.scalars(
        select(BodyMetric).where(BodyMetric.user_id == user.id, BodyMetric.date == day)
    ).first()
    created = row is None
    if created:
        row = BodyMetric(user_id=user.id, date=day, source="auto-sync")
        db.add(row)
        db.flush()  # 让后续同一天的查询能看到这一行
    for k, v in vals.items():
        if v is not None and hasattr(row, k):
            setattr(row, k, v)
    if not row.source:
        row.source = "auto-sync"
    return "added" if created else "updated"


def _ingest_metrics(db: OrmSession, user: User, metrics) -> dict:
    """支持两种形态：
    1) {"weight_kg": 74.2, ...}  （配合顶层 date）
    2) [{name, data:[{date, qty}]}]  （Health Auto Export）
    """
    added = updated = 0
    if isinstance(metrics, dict):
        day = None
        return {"pending_simple": metrics}

    if isinstance(metrics, list):
        for m in metrics:
            if not isinstance(m, dict):
                continue
            raw_name = str(m.get("name") or "").strip()
            field = _METRIC_MAP.get(raw_name.lower())
            if not field:
                # 未知指标：原样存进 health_samples，不丢数据
                for pt in m.get("data") or []:
                    if not isinstance(pt, dict):
                        continue
                    dt = _parse_dt(pt.get("date") or pt.get("startDate"))
                    if not dt:
                        continue
                    val = _qty(pt.get("qty") if pt.get("qty") is not None else pt.get("sum") or pt.get("avg"))
                    if val is None:
                        continue
                    _save_sample(db, user, dt.date(), raw_name, val, pt.get("units"))
                continue
            for pt in m.get("data") or []:
                if not isinstance(pt, dict):
                    continue
                dt = _parse_dt(pt.get("date") or pt.get("startDate"))
                if not dt:
                    continue
                if field == "sleep_hours":
                    # HAE 的 sleep_analysis 把各阶段分开给，需要累加真正的睡眠阶段
                    parts = []
                    for k in ("asleep", "asleepCore", "asleepDeep", "asleepREM", "core", "deep", "rem"):
                        v = _qty(pt.get(k))
                        if v is not None:
                            parts.append(v)
                    if parts:
                        val = sum(parts)
                    else:
                        val = _qty(pt.get("qty"))
                else:
                    val = _qty(pt)
                if val is None:
                    continue
                if field == "bodyfat_pct" and val <= 1.5:
                    val = round(val * 100, 1)
                res = _upsert_body(db, user, dt.date(), {field: round(val, 2)})
                if res == "added":
                    added += 1
                else:
                    updated += 1
    return {"added": added, "updated": updated}


def _ingest_workouts(db: OrmSession, user: User, workouts) -> int:
    n = 0
    for w in workouts or []:
        if not isinstance(w, dict):
            continue
        start = _parse_dt(w.get("start") or w.get("startDate") or w.get("date"))
        if not start:
            continue
        end = _parse_dt(w.get("end") or w.get("endDate"))
        duration = _qty(w.get("duration"))
        if duration is None and end:
            duration = (end - start).total_seconds()
        name = str(w.get("name") or "训练")
        dist = _qty(w.get("distance"))
        units = ((w.get("distance") or {}) if isinstance(w.get("distance"), dict) else {}).get("units", "")
        if dist is not None and str(units).lower() in ("km", "kilometers"):
            dist = dist * 1000.0

        ext = f"auto-{user.id}-{start.isoformat()}-{name}"
        dup = db.scalars(
            select(Run).where(Run.user_id == user.id, Run.external_id == ext)
        ).first()
        if dup:
            continue

        pr = parsers.ParsedRun(
            start_time=start.replace(tzinfo=None),
            activity_type="running" if "run" in name.lower() else "workout",
            name=name,
            distance_m=dist or 0.0,
            duration_s=float(duration or 0),
            avg_hr=_qty(w.get("avgHeartRate") or w.get("avg_hr")),
            max_hr=_qty(w.get("maxHeartRate") or w.get("max_hr")),
            calories=_qty(w.get("activeEnergy") or w.get("calories")),
            elevation_gain_m=_qty(w.get("elevationUp") or w.get("elevation_gain")),
            source="auto-sync",
            external_id=ext,
        )
        db.add(
            Run(
                user_id=user.id,
                start_time=pr.start_time,
                activity_type=pr.activity_type,
                name=pr.name,
                distance_m=pr.distance_m,
                duration_s=pr.duration_s,
                avg_hr=pr.avg_hr,
                max_hr=pr.max_hr,
                calories=pr.calories,
                elevation_gain_m=pr.elevation_gain_m,
                source=pr.source,
                external_id=pr.external_id,
            )
        )
        n += 1
    return n


class SyncPayload(BaseModel):
    date: str | None = None
    metrics: object | None = None
    workouts: object | None = None



# --------------------------------------------------------------------------
# 兼容 快捷指令「获取 URL 内容」的多种请求体：
#   a) application/json            -> HAE JSON
#   b) multipart/form-data + 文件  -> 快捷指令「请求体=文件」（HAE 默认 CSV）
#   c) text/csv                    -> 纯 CSV 文本
# --------------------------------------------------------------------------
_CSV_ALIASES = {
    "date": ["date", "startdate", "start date", "start", "day", "time", "日期", "开始时间"],
    "metric": ["metric", "type", "name", "指标", "类型"],
    "value": ["value", "qty", "amount", "值", "数值"],
    "unit": ["unit", "units", "单位"],
}


def _csv_pick(header_lower, key):
    for alias in _CSV_ALIASES.get(key, []):
        if alias in header_lower:
            return header_lower.index(alias)
    return None


def _ingest_csv_text(db: OrmSession, user: User, text: str) -> dict:
    """解析 HAE 导出的 CSV（宽表或长表），返回统计。

    性能要点：整份 CSV 先在内存里聚合（同一天同一指标只保留最后一条），
    再做一次批量 select + 批量 insert，避免逐行查库导致大文件超时。
    """
    import csv as _csv
    import io as _io

    text = text.lstrip("\ufeff")
    if not text.strip():
        return {"metrics": 0, "runs": 0}

    sample = text[:4096]
    delim = ","
    for cand in (",", ";", "\t"):
        if sample.count(cand) > sample.count(delim):
            delim = cand

    rows = list(_csv.reader(_io.StringIO(text), delimiter=delim))
    if not rows:
        return {"metrics": 0, "runs": 0}

    header = [h.strip() for h in rows[0]]
    hl = [h.lower() for h in header]

    c_date = _csv_pick(hl, "date")
    c_metric = _csv_pick(hl, "metric")
    c_value = _csv_pick(hl, "value")
    c_unit = _csv_pick(hl, "unit")

    # agg[(date, metric)] = (value, unit)
    agg: dict = {}
    body_agg: dict = {}   # {date: {field: value}}

    if c_date is not None and c_metric is not None and c_value is not None:
        # 长表
        need = max(c_date, c_metric, c_value)
        for row in rows[1:]:
            if len(row) <= need:
                continue
            dt = _parse_dt(row[c_date])
            if not dt:
                continue
            name = (row[c_metric] or "").strip()
            raw = (row[c_value] or "").strip()
            if not name or not raw:
                continue
            val = _qty(raw)
            if val is None:
                continue
            unit = (row[c_unit] or "").strip() if c_unit is not None and len(row) > c_unit else None
            day = dt.date()
            name = _norm_metric(name)
            field = _METRIC_MAP.get(name.lower())
            if field in _BODY_FIELDS:
                v = val * 100 if (field == "bodyfat_pct" and val <= 1.5) else val
                body_agg.setdefault(day, {})[field] = round(v, 2)
            else:
                agg[(day, name)] = (val, unit)
    else:
        # 宽表：第一列日期，其余每列一个指标
        if c_date is None:
            c_date = 0
        for row in rows[1:]:
            if len(row) <= c_date:
                continue
            dt = _parse_dt(row[c_date])
            if not dt:
                continue
            day = dt.date()
            for idx, h in enumerate(header):
                if idx == c_date or idx >= len(row):
                    continue
                raw = (row[idx] or "").strip()
                if not raw:
                    continue
                val = _qty(raw)
                if val is None:
                    continue
                h = _norm_metric(h)
                field = _METRIC_MAP.get(h.lower())
                if field in _BODY_FIELDS:
                    v = val * 100 if (field == "bodyfat_pct" and val <= 1.5) else val
                    body_agg.setdefault(day, {})[field] = round(v, 2)
                else:
                    agg[(day, h)] = (val, None)

    # ---- 写身体指标：按天合并，一天只 upsert 一次 ----
    for day, fields in body_agg.items():
        _upsert_body(db, user, day, fields)

    saved = len(agg) + sum(len(v) for v in body_agg.values())

    # ---- 写 health_samples：一次查出已有行，再批量写 ----
    if agg:
        days = {d for d, _ in agg}
        existing = {}
        for row in db.scalars(
            select(HealthSample).where(
                HealthSample.user_id == user.id,
                HealthSample.date.in_(days),
            )
        ).all():
            existing[(row.date, row.metric)] = row

        for (day, name), (val, unit) in agg.items():
            row = existing.get((day, name))
            if row is None:
                db.add(HealthSample(
                    user_id=user.id, date=day, metric=name,
                    value=val, unit=unit, source="auto-sync",
                ))
            else:
                row.value = val
                if unit:
                    row.unit = unit

    db.commit()
    return {"metrics": saved, "runs": 0}


_BODY_FIELDS = ("weight_kg", "bodyfat_pct", "resting_hr", "sleep_hours",
                "muscle_kg", "waist_cm", "hip_cm", "chest_cm", "arm_cm", "thigh_cm")

_SAMPLE_CACHE: dict = {}


# HAE 中文版导出的指标名形如「体重 (kg)」「静息心率 (count/min)」，
# 这里做一次归一化，把中文名和单位都剥掉，映射到英文标准名。
_CN_METRIC = {
    "\u4f53\u91cd": "weight_body_mass",
    "\u4f53\u91cd\u8d28\u91cf": "weight_body_mass",
    "\u4f53\u8102": "body_fat_percentage",
    "\u4f53\u8102\u767e\u5206\u6bd4": "body_fat_percentage",
    "\u9759\u606f\u5fc3\u7387": "resting_heart_rate",
    "\u5fc3\u7387": "heart_rate",
    "\u7761\u7720": "sleep_analysis",
    "\u7761\u7720\u5206\u6790": "sleep_analysis",
    "\u6b65\u6570": "step_count",
    "\u8eab\u9ad8": "height",
    "\u808c\u8089\u91cf": "lean_body_mass",
    "\u8170\u56f4": "waist_circumference",
    "\u4f53\u6e29": "body_temperature",
}


def _norm_metric(name: str) -> str:
    """把「体重 (kg)」这类中文名归一化成英文键，找不到就返回原名。"""
    raw = (name or "").strip()
    if not raw:
        return raw
    # 去掉括号里的单位
    base = raw.split("(")[0].split("（")[0].strip()
    hit = _CN_METRIC.get(base)
    if hit:
        return hit
    # 已是英文就直接返回
    return raw


def _csv_store(db: OrmSession, user: User, day, name: str, val: float, unit) -> None:
    """把一个 CSV 单元格写进 body_metrics 或 health_samples。

    注意：这里绝不 commit。逐行 commit 会让 3 万行 CSV 耗时 40 秒以上，
    导致 iPhone 快捷指令超时并报「网络连接已中断」。统一由调用方提交一次。
    """
    field = _METRIC_MAP.get(name.lower())
    if field in ("weight_kg", "bodyfat_pct", "resting_hr", "sleep_hours",
                 "muscle_kg", "waist_cm", "hip_cm", "chest_cm", "arm_cm", "thigh_cm"):
        v = val * 100 if (field == "bodyfat_pct" and val <= 1.5) else val
        _upsert_body(db, user, day, {field: round(v, 2)})
        return

    key = (day, name)
    row = _SAMPLE_CACHE.get(key)
    if row is None:
        row = db.scalars(
            select(HealthSample).where(
                HealthSample.user_id == user.id,
                HealthSample.date == day,
                HealthSample.metric == name,
            )
        ).first()
        _SAMPLE_CACHE[key] = row if row is not None else False
    if row is False or row is None:
        row = HealthSample(
            user_id=user.id, date=day, metric=name,
            value=val, unit=unit, source="auto-sync",
        )
        db.add(row)
        _SAMPLE_CACHE[key] = row
    else:
        row.value = val
        if unit:
            row.unit = unit


@router.post("/health")
async def receive_health(
    request: Request,
    authorization: str | None = Header(default=None),
    db: OrmSession = Depends(get_db),
):
    """接收第三方健康 App 推送的 JSON。

    鉴权：`Authorization: Bearer <sync_token>`
    """
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        token = request.query_params.get("token", "")
    user = _user_by_token(db, token)

    # 取原始字节（快捷指令「请求体=文件」会走 multipart，不是 JSON）
    raw = await request.body()
    ctype = (request.headers.get("content-type") or "").lower()

    body = None
    csv_text = None

    if "multipart/form-data" in ctype:
        # 从 multipart 里抠出文件内容
        import re as _re
        boundary = ""
        m = _re.search(r"boundary=([^;]+)", ctype)
        if m:
            boundary = m.group(1).strip().strip('"')
        if boundary:
            sep = ("--" + boundary).encode()
            parts = raw.split(sep)
            best = ""
            for part in parts:
                if b"\r\n\r\n" not in part:
                    continue
                head, _, content = part.partition(b"\r\n\r\n")
                txt = content.rstrip(b"\r\n-").decode("utf-8", "ignore").strip()
                # 优先带 filename 的文件片段；其次取最长的文本片段（兼容「表单」提交）
                if not txt:
                    continue
                if b"filename" in head and txt:
                    best = txt
                    break
                if len(txt) > len(best):
                    best = txt
            if best:
                csv_text = best
        if csv_text is None:
            csv_text = raw.decode("utf-8", "ignore")
    else:
        text = raw.decode("utf-8", "ignore").strip()
        if text.startswith("{") or text.startswith("["):
            try:
                body = json.loads(text)
            except Exception:  # noqa: BLE001
                raise HTTPException(400, "请求体不是合法 JSON")
        elif text:
            csv_text = text

    # ---- 分支 1：CSV（快捷指令「请求体=文件」最常见） ----
    if csv_text is not None:
        try:
            stat = _ingest_csv_text(db, user, csv_text)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"CSV 解析失败：{exc}") from exc
        db.commit()
        n = stat.get("metrics", 0) + stat.get("runs", 0)
        _touch_last_sync(db, user, {"csv_metrics": stat.get("metrics", 0), "csv_runs": stat.get("runs", 0)})
        db.commit()
        return {
            "ok": True,
            "user": user.username,
            "format": "csv",
            "metrics_imported": stat.get("metrics", 0),
            "workouts_imported": stat.get("runs", 0),
            "rows": n,
            "at": datetime.now(CN_TZ).isoformat(timespec="seconds"),
        }

    if not isinstance(body, dict):
        raise HTTPException(400, "请求体必须是 JSON 对象或 CSV 文本")

    # 兼容快捷指令「JSON 请求体 + 单字段包 CSV」的写法：
    #   {"导出锻炼": "Date,Metric,Value,Unit\n..."}
    #   {"anything": "..."} 只要值里像 CSV（有换行且含逗号）就转去 CSV 解析
    if "data" not in body and "metrics" not in body and "workouts" not in body:
        for _k, _v in body.items():
            if isinstance(_v, str) and "\n" in _v and "," in _v:
                try:
                    st = _ingest_csv_text(db, user, _v)
                except Exception:  # noqa: BLE001
                    break
                db.commit()
                _touch_last_sync(db, user, {"csv_metrics": st.get("metrics", 0)})
                db.commit()
                return {
                    "ok": True,
                    "user": user.username,
                    "format": "json-wrapped-csv",
                    "metrics_imported": st.get("metrics", 0),
                    "workouts_imported": st.get("runs", 0),
                    "at": datetime.now(CN_TZ).isoformat(timespec="seconds"),
                }

    # 兼容 Health Auto Export 的外层 data
    payload = body.get("data") if isinstance(body.get("data"), dict) else body

    body_added = body_updated = 0
    runs_added = 0

    # 1) 简单格式：{"date": "...", "metrics": {"weight_kg": ...}}
    simple = payload.get("metrics")
    day_str = payload.get("date") or payload.get("day")
    if isinstance(simple, dict) and simple:
        day = None
        if day_str:
            dt = _parse_dt(day_str)
            day = dt.date() if dt else None
        day = day or datetime.now(CN_TZ).date()
        vals = {}
        for k, v in simple.items():
            key = _METRIC_MAP.get(str(k).lower(), str(k))
            if key in ("weight_kg", "bodyfat_pct", "resting_hr", "sleep_hours",
                       "muscle_kg", "waist_cm", "hip_cm", "chest_cm", "arm_cm", "thigh_cm"):
                fv = _qty(v)
                if fv is not None:
                    if key == "bodyfat_pct" and fv <= 1.5:
                        fv = round(fv * 100, 1)
                    vals[key] = round(fv, 2)
        if vals:
            res = _upsert_body(db, user, day, vals)
            if res == "added":
                body_added += 1
            else:
                body_updated += 1

    # 2) Health Auto Export 完整格式
    elif isinstance(simple, list):
        r = _ingest_metrics(db, user, simple)
        body_added += r.get("added", 0)
        body_updated += r.get("updated", 0)

    # 3) 训练记录
    workouts = payload.get("workouts")
    if isinstance(workouts, list):
        runs_added = _ingest_workouts(db, user, workouts)

    _touch_last_sync(
        db,
        user,
        {
            "body_added": body_added,
            "body_updated": body_updated,
            "workouts": runs_added,
        },
    )
    db.commit()
    return {
        "ok": True,
        "user": user.username,
        "body_days_added": body_added,
        "body_days_updated": body_updated,
        "workouts_imported": runs_added,
        "at": datetime.now(CN_TZ).isoformat(timespec="seconds"),
    }


@router.get("/alive")
def alive():
    """无鉴权连通性检查：手机 Safari 打开这个地址，能返回 JSON 说明网络通。"""
    return {"ok": True, "app": "GRF", "msg": "network ok"}


@router.get("/ping")
def sync_ping(authorization: str | None = Header(default=None), db: OrmSession = Depends(get_db)):
    """给手机端做连通性测试用。"""
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    user = _user_by_token(db, token)
    return {"ok": True, "user": user.username, "message": "令牌有效，可以开始同步"}

@router.get("/status")
def sync_status(request: Request, db: OrmSession = Depends(get_db)):
    """网页端用：查看是否已生成令牌、最近一次同步时间与累计数据量。"""
    from .security import current_user
    from .models import AppSetting
    import json as _json
    from sqlalchemy import func

    user = current_user(request, db)
    row = db.get(AppSetting, "last_sync_%d" % user.id)
    last = None
    if row and row.value:
        try:
            last = _json.loads(row.value)
        except Exception:  # noqa: BLE001
            last = None

    body_cnt = db.scalar(
        select(func.count()).select_from(BodyMetric).where(
            BodyMetric.user_id == user.id, BodyMetric.source == "auto-sync"
        )
    ) or 0
    run_cnt = db.scalar(
        select(func.count()).select_from(Run).where(
            Run.user_id == user.id, Run.source == "auto-sync"
        )
    ) or 0

    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "127.0.0.1:7788"
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme

    return {
        "ok": True,
        "has_token": bool(user.sync_token),
        "endpoint": "%s://%s/api/sync/health" % (proto, host),
        "last_sync": last,
        "auto_body_days": body_cnt,
        "auto_runs": run_cnt,
    }

# ==========================================================================
# 一键快捷指令：动态生成内置 endpoint + token 的 .shortcut 文件
# ==========================================================================
def _xml_escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _act_ref(uuid: str, name: str) -> str:
    """引用某个动作输出（作为输入用）。"""
    return (
        "<dict><key>Value</key><dict>"
        "<key>Type</key><string>ActionOutput</string>"
        "<key>OutputUUID</key><string>%s</string>"
        "<key>OutputName</key><string>%s</string>"
        "</dict><key>WFSerializationType</key><string>WFTextTokenAttachment</string></dict>"
        % (uuid, _xml_escape(name))
    )


def build_shortcut_plist(endpoint: str, token: str) -> bytes:
    """生成 iOS 快捷指令（.shortcut / plist）。

    内置 endpoint 与 token，用户导入后无需填写任何内容，
    点运行即自动读取健康数据并 POST 到服务器。
    """
    U = {
        "weight": "11111111-0000-0000-0000-000000000001",
        "fat": "11111111-0000-0000-0000-000000000002",
        "rhr": "11111111-0000-0000-0000-000000000003",
        "date": "11111111-0000-0000-0000-000000000004",
        "day": "11111111-0000-0000-0000-000000000005",
        "text": "11111111-0000-0000-0000-000000000006",
        "post": "11111111-0000-0000-0000-000000000007",
    }

    def health_action(qtype: str, unit: str) -> str:
        return (
            "<dict><key>WFWorkflowActionIdentifier</key>"
            "<string>is.workflow.actions.gethealthsample</string>"
            "<key>WFWorkflowActionParameters</key><dict>"
            "<key>WFHealthQuantityType</key><string>%s</string>"
            "<key>WFHealthSampleType</key><string>Most Recent</string>"
            "<key>WFHealthSampleCount</key><integer>1</integer>"
            "<key>WFHealthUnit</key><string>%s</string>"
            "</dict></dict>" % (qtype, unit)
        )

    # JSON 模板：四个占位符依次是 日期 / 体重 / 体脂 / 静息心率
    tpl_parts = ['{"date":"', '","metrics":{"weight_kg":', ',"bodyfat_pct":', ',"resting_hr":', "}}"]
    tpl = "".join([tpl_parts[0], "\ufffc", tpl_parts[1], "\ufffc", tpl_parts[2], "\ufffc", tpl_parts[3], "\ufffc", tpl_parts[4]])

    # 计算每个 \ufffc 的字符偏移
    pos = []
    idx = 0
    for i, ch in enumerate(tpl):
        if ch == "\ufffc":
            pos.append(i)
    assert len(pos) == 4, pos

    def attach(offset: int, uuid: str, name: str) -> str:
        return (
            "<key>{%d, 1}</key><dict>"
            "<key>Type</key><string>ActionOutput</string>"
            "<key>OutputUUID</key><string>%s</string>"
            "<key>OutputName</key><string>%s</string>"
            "</dict>" % (offset, uuid, _xml_escape(name))
        )

    attachments = "".join([
        attach(pos[0], U["day"], "格式化后的日期"),
        attach(pos[1], U["weight"], "体重"),
        attach(pos[2], U["fat"], "体脂率"),
        attach(pos[3], U["rhr"], "静息心率"),
    ])

    text_action = (
        "<dict><key>WFWorkflowActionIdentifier</key>"
        "<string>is.workflow.actions.gettext</string>"
        "<key>WFWorkflowActionParameters</key><dict>"
        "<key>UUID</key><string>%s</string>"
        "<key>WFText</key><dict>"
        "<key>WFSerializationType</key><string>WFTextTokenString</string>"
        "<key>Value</key><dict>"
        "<key>string</key><string>%s</string>"
        "<key>attachmentsByRange</key><dict>%s</dict>"
        "</dict></dict>"
        "</dict></dict>" % (U["text"], _xml_escape(tpl), attachments)
    )

    actions = "".join([
        # 1 体重
        "<dict><key>WFWorkflowActionIdentifier</key><string>is.workflow.actions.gethealthsample</string>"
        "<key>WFWorkflowActionParameters</key><dict>"
        "<key>UUID</key><string>%s</string>"
        "<key>WFHealthQuantityType</key><string>HKQuantityTypeIdentifierBodyMass</string>"
        "<key>WFHealthSampleType</key><string>Most Recent</string>"
        "<key>WFHealthSampleCount</key><integer>1</integer>"
        "<key>WFHealthUnit</key><string>kg</string>"
        "</dict></dict>" % U["weight"],
        # 2 体脂
        "<dict><key>WFWorkflowActionIdentifier</key><string>is.workflow.actions.gethealthsample</string>"
        "<key>WFWorkflowActionParameters</key><dict>"
        "<key>UUID</key><string>%s</string>"
        "<key>WFHealthQuantityType</key><string>HKQuantityTypeIdentifierBodyFatPercentage</string>"
        "<key>WFHealthSampleType</key><string>Most Recent</string>"
        "<key>WFHealthSampleCount</key><integer>1</integer>"
        "<key>WFHealthUnit</key><string>%%</string>"
        "</dict></dict>" % U["fat"],
        # 3 静息心率
        "<dict><key>WFWorkflowActionIdentifier</key><string>is.workflow.actions.gethealthsample</string>"
        "<key>WFWorkflowActionParameters</key><dict>"
        "<key>UUID</key><string>%s</string>"
        "<key>WFHealthQuantityType</key><string>HKQuantityTypeIdentifierRestingHeartRate</string>"
        "<key>WFHealthSampleType</key><string>Most Recent</string>"
        "<key>WFHealthSampleCount</key><integer>1</integer>"
        "<key>WFHealthUnit</key><string>count/min</string>"
        "</dict></dict>" % U["rhr"],
        # 4 当前日期
        "<dict><key>WFWorkflowActionIdentifier</key><string>is.workflow.actions.date</string>"
        "<key>WFWorkflowActionParameters</key><dict>"
        "<key>UUID</key><string>%s</string>"
        "<key>WFDateActionMode</key><string>Current Date</string>"
        "</dict></dict>" % U["date"],
        # 5 格式化
        "<dict><key>WFWorkflowActionIdentifier</key><string>is.workflow.actions.format.date</string>"
        "<key>WFWorkflowActionParameters</key><dict>"
        "<key>UUID</key><string>%s</string>"
        "<key>WFDateFormatStyle</key><string>Custom</string>"
        "<key>WFDateFormat</key><string>yyyy-MM-dd</string>"
        "<key>WFInput</key>%s"
        "</dict></dict>" % (U["day"], _act_ref(U["date"], "日期")),
        # 6 构造 JSON
        text_action,
        # 7 POST
        "<dict><key>WFWorkflowActionIdentifier</key><string>is.workflow.actions.downloadurl</string>"
        "<key>WFWorkflowActionParameters</key><dict>"
        "<key>UUID</key><string>%s</string>"
        "<key>WFURL</key><string>%s</string>"
        "<key>WFHTTPMethod</key><string>POST</string>"
        "<key>WFHTTPBodyType</key><string>JSON</string>"
        "<key>WFJSONValues</key>%s"
        "<key>WFHTTPHeaders</key><dict>"
        "<key>Value</key><dict><key>WFDictionaryFieldValueItems</key><array>"
        "<dict><key>WFItemType</key><integer>0</integer>"
        "<key>WFKey</key><dict><key>Value</key><dict><key>string</key><string>Authorization</string></dict>"
        "<key>WFSerializationType</key><string>WFTextTokenString</string></dict>"
        "<key>WFValue</key><dict><key>Value</key><dict><key>string</key><string>Bearer %s</string></dict>"
        "<key>WFSerializationType</key><string>WFTextTokenString</string></dict></dict>"
        "</array></dict><key>WFSerializationType</key><string>WFDictionaryFieldValue</string></dict>"
        "</dict></dict>" % (U["post"], _xml_escape(endpoint), _act_ref(U["text"], "文本"), _xml_escape(token)),
        # 8 显示结果
        "<dict><key>WFWorkflowActionIdentifier</key><string>is.workflow.actions.showresult</string>"
        "<key>WFWorkflowActionParameters</key><dict>"
        "<key>Text</key>%s"
        "</dict></dict>" % _act_ref(U["post"], "URL 的内容"),
    ])

    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        "<plist version=\"1.0\"><dict>"
        "<key>WFWorkflowActions</key><array>%s</array>"
        "<key>WFWorkflowClientVersion</key><string>1146.14</string>"
        "<key>WFWorkflowMinimumClientVersion</key><integer>900</integer>"
        "<key>WFWorkflowMinimumClientVersionString</key><string>900</string>"
        "<key>WFWorkflowIcon</key><dict>"
        "<key>WFWorkflowIconStartColor</key><integer>4282601983</integer>"
        "<key>WFWorkflowIconGlyphNumber</key><integer>59417</integer>"
        "</dict>"
        "<key>WFWorkflowImportQuestions</key><array/>"
        "<key>WFWorkflowTypes</key><array><string>NCWidget</string><string>WatchKit</string></array>"
        "<key>WFWorkflowInputContentItemClasses</key><array>"
        "<string>WFStringContentItem</string></array>"
        "</dict></plist>"
        % actions
    )
    return plist.encode("utf-8")


@router.get("/config")
def get_config(request: Request, db: OrmSession = Depends(get_db)):
    """返回可直接粘贴到快捷指令里的完整配置（纯文本）。"""
    from .security import current_user

    user = current_user(request, db)
    token = ensure_sync_token(db, user)
    # 手机端必须访问公网地址；本地调试时 request 头会是 127.0.0.1，不能用
    base = (getattr(settings, "PUBLIC_BASE_URL", "") or "").strip()
    if not base:
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "127.0.0.1:7788"
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        base = "%s://%s" % (proto, host)
    endpoint = base.rstrip("/") + "/api/sync/health"

    # 快捷指令「获取 URL 内容」里可以直接粘贴的 cURL
    curl = (
        "curl -X POST '%s' "
        "-H 'Authorization: Bearer %s' "
        "-H 'Content-Type: application/json' "
        '-d \'{"date":"2026-10-18","metrics":{"weight_kg":74.2,'
        '"bodyfat_pct":18.5,"resting_hr":57}}\''
        % (endpoint, token)
    )
    # 关键：把令牌直接拼进 URL，快捷指令就完全不需要配「头部」键值对。
    # 实测（零 header）返回 200，这是绕开 iOS 头部输入框最稳的做法。
    url_with_token = "%s?token=%s" % (endpoint, token)

    return {
        "ok": True,
        "endpoint": endpoint,
        "url": url_with_token,
        "token": token,
        "header": "Authorization: Bearer %s" % token,
        "curl": curl,
    }

@router.get("/samples")
def list_samples(
    days: int = Query(30, ge=1, le=365),
    metric: str | None = Query(None),
    request: Request = None,
    db: OrmSession = Depends(get_db),
):
    """查看已同步的通用健康指标。"""
    from .security import current_user
    from datetime import timedelta

    user = current_user(request, db)
    since = date.today() - timedelta(days=days)
    stmt = select(HealthSample).where(
        HealthSample.user_id == user.id, HealthSample.date >= since
    )
    if metric:
        stmt = stmt.where(HealthSample.metric == metric)
    rows = db.scalars(stmt.order_by(HealthSample.date.desc()).limit(2000)).all()

    grouped: dict[str, list] = {}
    for r in rows:
        grouped.setdefault(r.metric, []).append(
            {"date": r.date.isoformat(), "value": round(r.value, 2), "unit": r.unit}
        )
    return {
        "ok": True,
        "metrics": sorted(grouped.keys()),
        "count": len(rows),
        "data": grouped,
    }
