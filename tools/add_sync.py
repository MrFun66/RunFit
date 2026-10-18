# -*- coding: utf-8 -*-
import io
from pathlib import Path

ROOT = Path(r"D:\GRF")

def w(p, s):
    p.write_text(s, encoding="utf-8", newline="\n")

# ---------------- 1. models.py ----------------
mp = ROOT / "app" / "models.py"
s = mp.read_text(encoding="utf-8")
if "sync_token" not in s:
    anchor = '    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")'
    assert anchor in s, "timezone anchor missing"
    s = s.replace(anchor, anchor + '\n    sync_token: Mapped[str | None] = mapped_column(String(64), index=True)')
    w(mp, s)
    print("[1] models.py: sync_token added")
else:
    print("[1] models.py: already ok")

# ---------------- 2. db.py migration ----------------
dp = ROOT / "app" / "db.py"
s = dp.read_text(encoding="utf-8")
if "_ensure_columns" not in s:
    helper = '''def _ensure_columns() -> None:
    """SQLite 轻量迁移：给已存在的表补上新增列（create_all 不会改已有表）。"""
    wanted = {
        "users": {"sync_token": "VARCHAR(64)"},
    }
    with engine.begin() as conn:
        for table, cols in wanted.items():
            try:
                rows = conn.exec_driver_sql("PRAGMA table_info(%s)" % table).fetchall()
            except Exception:
                continue
            existing = {r[1] for r in rows}
            for name, ddl in cols.items():
                if name not in existing:
                    conn.exec_driver_sql(
                        "ALTER TABLE %s ADD COLUMN %s %s" % (table, name, ddl)
                    )


def init_db() -> None:'''
    s = s.replace("def init_db() -> None:", helper)
    s = s.replace("    Base.metadata.create_all(bind=engine)",
                  "    Base.metadata.create_all(bind=engine)\n    _ensure_columns()")
    w(dp, s)
    print("[2] db.py: migration added")
else:
    print("[2] db.py: already ok")

# ---------------- 3. api.py routes ----------------
ap = ROOT / "app" / "api.py"
s = ap.read_text(encoding="utf-8")
if "/sync/health" not in s:
    ADD = r"""

# ==========================================================================
# 健康数据自动同步（Health Auto Export / Health Connect 桥接 -> POST 到这里）
# ==========================================================================
_HAE_METRIC_MAP = {
    "weight_body_mass": "weight_kg",
    "body_mass": "weight_kg",
    "body_fat_percentage": "bodyfat_pct",
    "resting_heart_rate": "resting_hr",
    "lean_body_mass": "muscle_kg",
    "waist_circumference": "waist_cm",
    "sleep_analysis": "sleep_hours",
}


def _sync_parse_dt(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.utcfromtimestamp(float(v))
        except Exception:
            return None
    txt = str(v).strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(txt)
    except Exception:
        return None


def _sync_user(db: OrmSession, request: Request) -> User:
    tok = (request.headers.get("x-sync-token") or request.query_params.get("token") or "").strip()
    if not tok:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            tok = auth[7:].strip()
    if not tok:
        raise HTTPException(401, "缺少同步令牌（请求头 X-Sync-Token）")
    user = db.scalars(select(User).where(User.sync_token == tok)).first()
    if not user:
        raise HTTPException(401, "同步令牌无效，请在 我的-设置-健康数据自动同步 里重新生成")
    return user


def _sync_upsert_body(db: OrmSession, user_id: int, day: date, vals: dict) -> bool:
    row = db.scalars(
        select(BodyMetric).where(BodyMetric.user_id == user_id, BodyMetric.date == day)
    ).first()
    added = row is None
    if row is None:
        row = BodyMetric(user_id=user_id, date=day)
        db.add(row)
    for k, v in vals.items():
        if v is None or not hasattr(row, k):
            continue
        cur = getattr(row, k)
        if cur is None or (row.source or "") in ("auto", "sync"):
            try:
                setattr(row, k, round(float(v), 2))
            except (TypeError, ValueError):
                continue
    row.source = "auto"
    return added


def _sync_add_run(db: OrmSession, user_id: int, w: dict) -> bool:
    start = _sync_parse_dt(w.get("start") or w.get("start_time") or w.get("date"))
    if start is None:
        return False
    ext = "sync_" + start.strftime("%Y%m%d%H%M%S")
    dup = db.scalars(
        select(Run).where(Run.user_id == user_id, Run.external_id == ext)
    ).first()
    if dup:
        return False

    dist_m = None
    dist = w.get("distance")
    if isinstance(dist, dict):
        qty = dist.get("qty")
        unit = str(dist.get("units") or "km").lower()
        if qty is not None:
            f = 1000.0 if unit.startswith("k") else (1609.34 if unit.startswith("mi") else 1.0)
            dist_m = round(float(qty) * f, 1)
    elif isinstance(dist, (int, float)):
        dist_m = float(dist)

    dur_s = None
    dur = w.get("duration")
    if isinstance(dur, (int, float)):
        dur_s = float(dur)
    elif isinstance(dur, dict) and dur.get("qty") is not None:
        dur_s = float(dur["qty"])

    avg_hr = None
    hr = w.get("heartRate") or w.get("avgHeartRate")
    if isinstance(hr, dict):
        avg = hr.get("avg")
        if isinstance(avg, dict):
            avg_hr = avg.get("qty")
        elif isinstance(avg, (int, float)):
            avg_hr = avg
    elif isinstance(hr, (int, float)):
        avg_hr = hr

    kcal = None
    cal = w.get("activeEnergyBurned") or w.get("totalEnergy")
    if isinstance(cal, dict):
        kcal = cal.get("qty")
    elif isinstance(cal, (int, float)):
        kcal = cal

    db.add(Run(
        user_id=user_id,
        start_time=start,
        activity_type="running",
        name=str(w.get("name") or "同步训练")[:120],
        distance_m=dist_m,
        duration_s=dur_s,
        moving_s=dur_s,
        avg_hr=float(avg_hr) if avg_hr is not None else None,
        calories=float(kcal) if kcal is not None else None,
        source="sync",
        source_file="auto-sync",
        external_id=ext,
    ))
    return True


def _sync_apply(db: OrmSession, user: User, payload: dict) -> dict:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    per_day: dict[str, dict] = {}

    metrics = data.get("metrics")
    if isinstance(metrics, list):
        for m in metrics:
            if not isinstance(m, dict):
                continue
            key = _HAE_METRIC_MAP.get(str(m.get("name") or "").strip().lower())
            if not key:
                continue
            for p in (m.get("data") or []):
                if not isinstance(p, dict):
                    continue
                dt = _sync_parse_dt(p.get("date") or p.get("startDate") or p.get("sleepEnd"))
                if dt is None:
                    continue
                if key == "sleep_hours":
                    v = p.get("asleep")
                    if v is None:
                        v = p.get("totalSleep", p.get("qty"))
                else:
                    v = p.get("qty", p.get("value"))
                if v is None:
                    continue
                try:
                    per_day.setdefault(dt.date().isoformat(), {})[key] = float(v)
                except (TypeError, ValueError):
                    continue

    for row in (data.get("body") or []):
        if not isinstance(row, dict):
            continue
        dt = _sync_parse_dt(row.get("date"))
        if dt is None:
            continue
        tgt = per_day.setdefault(dt.date().isoformat(), {})
        for k in ("weight_kg", "bodyfat_pct", "resting_hr", "sleep_hours", "muscle_kg", "waist_cm"):
            if row.get(k) is not None:
                tgt[k] = row[k]

    added = updated = 0
    for day_str, vals in per_day.items():
        try:
            d = date.fromisoformat(day_str)
        except ValueError:
            continue
        if _sync_upsert_body(db, user.id, d, vals):
            added += 1
        else:
            updated += 1

    runs = 0
    workouts = data.get("workouts") or []
    runs_in = data.get("runs") or []
    for w in list(workouts) + list(runs_in):
        if isinstance(w, dict) and _sync_add_run(db, user.id, w):
            runs += 1

    db.commit()
    return {"body_days_added": added, "body_days_updated": updated, "runs_imported": runs}


@router.post("/sync/health")
async def sync_health(request: Request, db: OrmSession = Depends(get_db)):
    """接收 Health Auto Export / Health Connect 桥接工具推送的健康数据。"""
    user = _sync_user(db, request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "请求体必须是 JSON")
    if not isinstance(payload, dict):
        raise HTTPException(400, "JSON 顶层必须是对象")
    return {"ok": True, **_sync_apply(db, user, payload)}


@router.get("/sync/token")
def get_sync_token(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    tok = user.sync_token or ""
    return {"configured": bool(tok), "token": tok, "endpoint": "/api/sync/health",
            "hint": "请求头 X-Sync-Token 填这个值"}


@router.post("/sync/token")
def create_sync_token(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    tok = ("grf_" + uuid.uuid4().hex + uuid.uuid4().hex)[:64]
    user.sync_token = tok
    db.add(user)
    db.commit()
    return {"ok": True, "token": tok, "endpoint": "/api/sync/health"}


@router.delete("/sync/token")
def delete_sync_token(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    user.sync_token = None
    db.add(user)
    db.commit()
    return {"ok": True}
"""
    s = s.rstrip("\n") + ADD
    w(ap, s)
    print("[3] api.py: sync routes appended")
else:
    print("[3] api.py: already ok")
print("done")
