"""API 路由。"""
from __future__ import annotations

import base64
import json
import re
import shutil
import uuid
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as OrmSession

from . import analytics, foods, llm, nutrition, parsers, strength
from . import foods as foods_mod
from .llm_config import get_cfg, has_own_cfg, is_owner
from .config import settings
from .db import get_db
from .exercises_seed import seed_exercises
from .models import (
    BodyMetric,
    CoachMessage,
    Exercise,
    Meal,
    NutritionDay,
    Run,
    TemplateItem,
    User,
    Workout,
    WorkoutSet,
    WorkoutTemplate,
)
from .models import Session as UserSession
from .security import (
    create_session,
    current_user,
    first_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api")


# ==========================================================================
# 工具
# ==========================================================================
def _age(birth_year: int | None) -> int | None:
    return (date.today().year - birth_year) if birth_year else None


def _user_profile(db: OrmSession, user: User) -> dict:
    last_bm = db.scalars(
        select(BodyMetric).where(BodyMetric.user_id == user.id).order_by(BodyMetric.date.desc()).limit(1)
    ).first()
    obs_max_hr = db.scalar(
        select(func.max(Run.max_hr)).where(Run.user_id == user.id, Run.max_hr.is_not(None))
    )
    age = _age(user.birth_year)
    hr_max = analytics.max_hr_estimate(age, obs_max_hr)
    hr_rest = last_bm.resting_hr if last_bm and last_bm.resting_hr else 60.0

    weight = last_bm.weight_kg if last_bm else None
    bodyfat = last_bm.bodyfat_pct if last_bm else None
    return {
        "username": user.username,
        "sex": user.sex,
        "age": age,
        "height_cm": user.height_cm,
        "weight_kg": weight,
        "bodyfat_pct": bodyfat,
        "target_weight_kg": user.target_weight_kg,
        "goal": user.goal,
        "activity_level": user.activity_level,
        "training_days_per_week": user.training_days_per_week,
        "hr_max": round(hr_max),
        "hr_rest": hr_rest,
        "diet_notes": user.diet_notes,
        "injury_notes": user.injury_notes,
    }


def _run_dict(r: Run) -> dict:
    dist_km = (r.distance_m or 0) / 1000.0
    dur = r.moving_s or r.duration_s or 0
    pace_s = dur / dist_km if dist_km > 0 else None
    return {
        "id": r.id,
        "start_time": r.start_time.isoformat() if r.start_time else None,
        "name": r.name,
        "activity_type": r.activity_type,
        "distance_m": r.distance_m,
        "duration_s": r.duration_s,
        "moving_s": r.moving_s,
        "avg_hr": r.avg_hr,
        "max_hr": r.max_hr,
        "avg_cadence": r.avg_cadence,
        "elevation_gain_m": r.elevation_gain_m,
        "calories": r.calories,
        "source": r.source,
        "samples_json": r.samples_json,
        "splits_json": r.splits_json,
        "pace": analytics.pace_str(r.distance_m, dur),
        "avg_pace_s_per_km": round(pace_s, 1) if pace_s else None,
        "splits": json.loads(r.splits_json) if r.splits_json else [],
    }


def _workout_dict(w: Workout) -> dict:
    return {
        "id": w.id,
        "date": w.date.isoformat(),
        "name": w.name,
        "focus": w.focus,
        "duration_min": w.duration_min,
        "rpe": w.rpe,
        "notes": w.notes,
        "sets": [
            {
                "id": s.id,
                "exercise_id": s.exercise_id,
                "exercise_name": s.exercise.name if s.exercise else None,
                "primary_muscles": s.exercise.primary_muscles if s.exercise else "[]",
                "secondary_muscles": s.exercise.secondary_muscles if s.exercise else "[]",
                "reps": s.reps,
                "weight_kg": s.weight_kg,
                "rpe": s.rpe,
                "is_warmup": s.is_warmup,
                "rest_s": s.rest_s,
                "note": s.note,
            }
            for s in w.sets
        ],
    }


# ==========================================================================
# 认证
# ==========================================================================
class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


@router.get("/auth/status")
def auth_status(request: Request, db: OrmSession = Depends(get_db)):
    has_user = first_user(db) is not None
    try:
        u = current_user(request, db)
        return {"registered": has_user, "logged_in": True, "username": u.username}
    except HTTPException:
        return {"registered": has_user, "logged_in": False, "username": None}


@router.post("/auth/register")
def register(body: RegisterIn, response: Response, db: OrmSession = Depends(get_db)):
    if first_user(db) is not None and not settings.ALLOW_REGISTER:
        raise HTTPException(403, "已存在用户，注册已关闭")
    if db.scalars(select(User).where(User.username == body.username)).first():
        raise HTTPException(400, "用户名已存在")
    u = User(username=body.username, password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    seed_exercises(db)
    sess = create_session(db, u)
    response.set_cookie(
        settings.SESSION_COOKIE, sess.token,
        httponly=True, samesite="lax", max_age=settings.SESSION_TTL_HOURS * 3600,
        secure=False,
    )
    return {"ok": True, "username": u.username}


@router.post("/auth/login")
def login(body: LoginIn, response: Response, db: OrmSession = Depends(get_db)):
    u = db.scalars(select(User).where(User.username == body.username)).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    sess = create_session(db, u)
    response.set_cookie(
        settings.SESSION_COOKIE, sess.token,
        httponly=True, samesite="lax", max_age=settings.SESSION_TTL_HOURS * 3600,
        secure=False,
    )
    return {"ok": True, "username": u.username}


class PasswordIn(BaseModel):
    old_password: str
    new_password: str


@router.post("/auth/password")
def change_password(
    body: PasswordIn,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """修改当前用户密码。"""
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "当前密码不正确")
    if len(body.new_password) < 8:
        raise HTTPException(400, "新密码至少 8 位")
    if body.new_password == body.old_password:
        raise HTTPException(400, "新密码不能与当前密码相同")
    user.password_hash = hash_password(body.new_password)
    db.add(user)
    db.commit()
    return {"ok": True, "message": "密码已更新"}


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: OrmSession = Depends(get_db)):
    tok = request.cookies.get(settings.SESSION_COOKIE)
    if tok:
        db.execute(delete(__import__("app.models", fromlist=["Session"]).Session).where(
            __import__("app.models", fromlist=["Session"]).Session.token == tok
        ))
        db.commit()
    response.delete_cookie(settings.SESSION_COOKIE)
    return {"ok": True}


# ==========================================================================
# 档案
# ==========================================================================
class ProfileIn(BaseModel):
    sex: str | None = None
    birth_year: int | None = None
    height_cm: float | None = None
    # 体重/体脂：若同时给了，会顺带写一条当天体测记录，保持历史可回溯
    weight_kg: float | None = None
    bodyfat_pct: float | None = None
    hr_max: int | None = None
    hr_rest: int | None = None
    target_weight_kg: float | None = None
    target_bodyfat_pct: float | None = None
    goal: str | None = None
    activity_level: str | None = None
    training_days_per_week: int | None = None
    diet_notes: str | None = None
    injury_notes: str | None = None
    timezone: str | None = None


@router.get("/profile")
def read_profile(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    return {
        **_user_profile(db, user),
        "birth_year": user.birth_year,
        "target_bodyfat_pct": user.target_bodyfat_pct,
        "onboarded": user.onboarded,
        "llm_configured": get_cfg(db, user).configured,
        "llm_own": has_own_cfg(db, user),
        "zones": analytics.hr_zones(
            _user_profile(db, user)["hr_max"], _user_profile(db, user)["hr_rest"]
        ),
    }


@router.put("/profile")
def update_profile(body: ProfileIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)

    # 体重 / 体脂 / 静息心率不在 User 表上，写入「今天」的体测记录（已有则合并）
    bm_fields = {}
    for k in ("weight_kg", "bodyfat_pct", "hr_rest"):
        if data.get(k) is not None:
            bm_fields[k] = data.pop(k)
    # hr_max 仅在 User 上有对应列时写入，否则丢弃（由历史跑步数据自动估算）
    if data.get("hr_max") is not None and not hasattr(user, "hr_max"):
        data.pop("hr_max")

    for k, v in data.items():
        if hasattr(user, k) and v is not None:
            setattr(user, k, v)

    if bm_fields:
        today = date.today()
        bm = db.scalars(
            select(BodyMetric).where(BodyMetric.user_id == user.id, BodyMetric.date == today)
        ).first()
        if bm is None:
            bm = BodyMetric(user_id=user.id, date=today)
            db.add(bm)
        if "hr_rest" in bm_fields:
            bm.resting_hr = bm_fields.pop("hr_rest")
        for k, v in bm_fields.items():
            setattr(bm, k, v)

    user.onboarded = True
    db.commit()
    return {"ok": True}


# ==========================================================================
# 身体指标
# ==========================================================================
class BodyIn(BaseModel):
    date: date
    weight_kg: float | None = None
    bodyfat_pct: float | None = None
    muscle_kg: float | None = None
    waist_cm: float | None = None
    hip_cm: float | None = None
    chest_cm: float | None = None
    arm_cm: float | None = None
    thigh_cm: float | None = None
    resting_hr: float | None = None
    sleep_hours: float | None = None
    note: str | None = None


@router.post("/body")
def upsert_body(body: BodyIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    row = db.scalars(
        select(BodyMetric).where(BodyMetric.user_id == user.id, BodyMetric.date == body.date)
    ).first()
    if not row:
        row = BodyMetric(user_id=user.id, date=body.date)
        db.add(row)
    for k, v in body.model_dump(exclude={"date"}).items():
        if v is not None:
            setattr(row, k, v)
    db.commit()
    return {"ok": True, "id": row.id}


@router.get("/body")
def list_body(
    days: int = Query(180, ge=1, le=3650),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=days)
    rows = db.scalars(
        select(BodyMetric)
        .where(BodyMetric.user_id == user.id, BodyMetric.date >= cutoff)
        .order_by(BodyMetric.date)
    ).all()
    return {
        "items": [
            {
                "date": r.date.isoformat(),
                "weight_kg": r.weight_kg,
                "bodyfat_pct": r.bodyfat_pct,
                "waist_cm": r.waist_cm,
                "resting_hr": r.resting_hr,
                "sleep_hours": r.sleep_hours,
            }
            for r in rows
        ],
        "trend": nutrition.weight_trend([(r.date, r.weight_kg) for r in rows if r.weight_kg]),
    }


# ==========================================================================
# 跑步
# ==========================================================================
@router.get("/runs")
def list_runs(
    limit: int = Query(100, ge=1, le=2000),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    rows = db.scalars(
        select(Run).where(Run.user_id == user.id).order_by(Run.start_time.desc()).limit(limit)
    ).all()
    return {"items": [{k: v for k, v in _run_dict(r).items() if k != "samples_json"} for r in rows]}


@router.get("/runs/{run_id:int}")
def get_run(run_id: int, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    r = db.get(Run, run_id)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "记录不存在")
    prof = _user_profile(db, user)
    d = _run_dict(r)
    return {
        **d,
        "analysis": analytics.analyze_run(d, prof["hr_max"], prof["hr_rest"]),
        "hr_zones": analytics.hr_zones(prof["hr_max"], prof["hr_rest"]),
    }


@router.delete("/runs/{run_id:int}")
def delete_run(run_id: int, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    r = db.get(Run, run_id)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "记录不存在")
    db.delete(r)
    db.commit()
    return {"ok": True}


def _save_parsed(db: OrmSession, user_id: int, pr: parsers.ParsedRun, filename: str) -> Run | None:
    if pr.external_id:
        dup = db.scalars(
            select(Run).where(Run.user_id == user_id, Run.external_id == pr.external_id)
        ).first()
        if dup:
            return None
    samples = [
        {"t": round(s.t, 1), "hr": s.hr, "cad": s.cadence, "speed": s.speed, "elev": s.elev}
        for s in parsers.downsample(pr.samples, 900)
    ]
    r = Run(
        user_id=user_id,
        start_time=pr.start_time,
        activity_type=pr.activity_type,
        name=pr.name,
        distance_m=round(pr.distance_m, 1) if pr.distance_m else None,
        duration_s=round(pr.duration_s, 1) if pr.duration_s else None,
        moving_s=round(pr.moving_s, 1) if pr.moving_s else None,
        avg_hr=round(pr.avg_hr, 1) if pr.avg_hr else None,
        max_hr=round(pr.max_hr, 1) if pr.max_hr else None,
        avg_cadence=round(pr.avg_cadence, 1) if pr.avg_cadence else None,
        elevation_gain_m=round(pr.elevation_gain_m, 1) if pr.elevation_gain_m else None,
        calories=round(pr.calories, 1) if pr.calories else None,
        source=pr.source,
        source_file=filename,
        external_id=pr.external_id,
        samples_json=json.dumps(samples),
        splits_json=json.dumps(pr.splits, ensure_ascii=False) if pr.splits else None,
        raw_meta=json.dumps(pr.meta, ensure_ascii=False, default=str)[:4000] if pr.meta else None,
    )
    db.add(r)
    return r


@router.post("/runs/upload")
async def upload_runs(
    files: list[UploadFile] | None = File(None),
    file: UploadFile | None = File(None),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    imported, skipped, errors = 0, 0, []
    batch: list[UploadFile] = list(files or [])
    if file is not None:
        batch.append(file)
    if not batch:
        raise HTTPException(400, "没有收到文件（字段名用 files 或 file）")
    for f in batch:
        name = f.filename or "upload"
        suffix = Path(name).suffix.lower()
        if suffix not in (".tcx", ".gpx", ".xml", ".csv", ".fit"):
            errors.append(f"{name}: 不支持的类型 {suffix}")
            continue
        dest = settings.UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
        with dest.open("wb") as fh:
            shutil.copyfileobj(f.file, fh)
        try:
            if suffix == ".fit":
                errors.append(f"{name}: FIT 暂不支持，请导出 TCX")
                continue
            parsed = parsers.parse_file(dest)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: 解析失败 {exc}")
            continue
        if not parsed:
            errors.append(f"{name}: 没有识别到训练记录")
            continue
        for pr in parsed:
            if _save_parsed(db, user.id, pr, name):
                imported += 1
            else:
                skipped += 1
        db.commit()
    return {"imported": imported, "skipped_duplicates": skipped, "errors": errors}


@router.get("/runs/stats")
def run_stats(
    weeks: int = Query(12, ge=1, le=104),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    prof = _user_profile(db, user)
    cutoff = datetime.now() - timedelta(weeks=weeks)
    rows = db.scalars(
        select(Run).where(Run.user_id == user.id, Run.start_time >= cutoff).order_by(Run.start_time)
    ).all()
    dicts = [_run_dict(r) for r in rows]
    summary = analytics.weekly_summary(dicts, prof["hr_max"], prof["hr_rest"])
    daily = [(r.start_time.date(), analytics.run_load(_run_dict(r), prof["hr_max"], prof["hr_rest"])) for r in rows]
    return {
        **summary,
        "acwr": analytics.acute_chronic_ratio(daily),
        "zones": analytics.hr_zones(prof["hr_max"], prof["hr_rest"]),
    }


# ==========================================================================
# 力量训练
# ==========================================================================
@router.get("/exercises")
def list_exercises(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    rows = db.scalars(
        select(Exercise).where((Exercise.owner_id == None) | (Exercise.owner_id == user.id)).order_by(Exercise.name)  # noqa: E711
    ).all()
    return {
        "items": [
            {
                "id": e.id,
                "name": e.name,
                "name_en": e.name_en,
                "category": e.category,
                "equipment": e.equipment,
                "is_compound": e.is_compound,
                "primary_muscles": json.loads(e.primary_muscles or "[]"),
                "secondary_muscles": json.loads(e.secondary_muscles or "[]"),
            }
            for e in rows
        ]
    }


class SetIn(BaseModel):
    exercise_id: int
    reps: int | None = None
    weight_kg: float | None = None
    rpe: float | None = None
    is_warmup: bool = False
    rest_s: int | None = None
    note: str | None = None


class WorkoutIn(BaseModel):
    date: date
    name: str | None = None
    focus: str | None = None
    duration_min: float | None = None
    rpe: float | None = None
    notes: str | None = None
    sets: list[SetIn] = []


@router.post("/workouts")
def create_workout(body: WorkoutIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    w = Workout(
        user_id=user.id,
        date=body.date,
        name=body.name,
        focus=body.focus,
        duration_min=body.duration_min,
        rpe=body.rpe,
        notes=body.notes,
    )
    db.add(w)
    db.flush()
    for i, s in enumerate(body.sets):
        db.add(WorkoutSet(workout_id=w.id, idx=i, **s.model_dump()))
    db.commit()
    db.refresh(w)
    return {"ok": True, "id": w.id}


@router.get("/workouts")
def list_workouts(
    limit: int = Query(60, ge=1, le=500),
    day: str | None = Query(None, alias="date"),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    stmt = select(Workout).where(Workout.user_id == user.id)
    if day:
        try:
            stmt = stmt.where(Workout.date == date.fromisoformat(day))
        except ValueError:
            raise HTTPException(400, "日期格式应为 YYYY-MM-DD")
    rows = db.scalars(stmt.order_by(Workout.date.desc(), Workout.id.desc()).limit(limit)).all()
    return {"items": [_workout_dict(w) for w in rows]}


@router.delete("/workouts/{wid:int}")
def delete_workout(wid: int, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    w = db.get(Workout, wid)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "记录不存在")
    db.delete(w)
    db.commit()
    return {"ok": True}


MUSCLE_TO_PART = {
    "chest": "chest",
    "lats": "back", "mid_back": "back", "lower_back": "back", "traps": "back",
    "front_delt": "shoulder", "side_delt": "shoulder", "rear_delt": "shoulder",
    "biceps": "arms", "triceps": "arms", "forearm": "arms",
    "quads": "legs", "hamstrings": "legs", "glutes": "legs", "calves": "legs",
    "abs": "core", "obliques": "core", "hip_flexor": "core",
}

PART_META = [
    ("chest", "\u80f8", "#f97316"),
    ("back", "\u80cc", "#0ea5e9"),
    ("shoulder", "\u80a9", "#a855f7"),
    ("arms", "\u624b\u81c2", "#22c55e"),
    ("legs", "\u817f", "#ef4444"),
    ("core", "\u6838\u5fc3", "#eab308"),
]


def _muscles_to_parts(raw) -> list:
    """exercise.primary_muscles 是 JSON 数组字符串，映射到六大部位。"""
    import json as _json
    if not raw:
        return []
    try:
        arr = _json.loads(raw) if isinstance(raw, str) else list(raw)
    except Exception:
        arr = [raw]
    parts = []
    for m in arr:
        p = MUSCLE_TO_PART.get(str(m).strip().lower())
        if p and p not in parts:
            parts.append(p)
    return parts


@router.get("/strength/trend")
def strength_trend(
    grain: str = Query("day", pattern="^(day|week|month|year)$"),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """力量训练容量图。
    日：今天的各部位容量（不同颜色=不同部位）
    周：本周 周一..周日，按月/年：x 轴为时间，颜色=训练部位堆叠
    """
    from collections import defaultdict

    today = date.today()

    def parts_of(st):
        ex = ex_map.get(st.exercise_id)
        parts = _muscles_to_parts(getattr(ex, "primary_muscles", None)) if ex else []
        if not parts and ex is not None:
            cat = (getattr(ex, "category", "") or "").lower()
            parts = {"push": ["chest"], "pull": ["back"], "legs": ["legs"], "core": ["core"]}.get(cat, ["core"])
        return parts or ["core"]

    def vol_of(st):
        v = float((st.weight_kg or 0) * (st.reps or 0))
        if v <= 0:
            v = float(st.reps or 0)
        return max(v, 0.0)

    ex_map = {e.id: e for e in db.scalars(select(Exercise)).all()}

    # ---------- 日：今天各部位 ----------
    if grain == "day":
        rows = db.scalars(
            select(Workout).where(Workout.user_id == user.id, Workout.date == today)
        ).all()
        agg = {p: 0.0 for p, _, _ in PART_META}
        for w in rows:
            for st in w.sets:
                if st.is_warmup:
                    continue
                v = vol_of(st)
                if v <= 0:
                    continue
                ps = parts_of(st)
                for p in ps:
                    agg[p] += v / len(ps)
        buckets, data, colors = [], [], []
        for p, label, color in PART_META:
            if agg[p] > 0:
                buckets.append({"key": p, "label": label})
                data.append(round(agg[p]))
                colors.append(color)
        total = round(sum(data))
        series = []
        if buckets:
            series.append({
                "part": "all", "label": "今日容量", "color": "#0ea5e9",
                "data": data, "colors": colors, "total": total, "sets": 0,
            })
        return {
            "grain": "day", "mode": "by_part", "buckets": buckets,
            "series": series, "total_volume": total, "active_buckets": len(buckets),
        }

    # ---------- 周 / 月 / 年：时间轴 ----------
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    if grain == "week":
        monday = today - timedelta(days=today.weekday())
        buckets = [((monday + timedelta(days=k)).isoformat(), weekday_names[k]) for k in range(7)]
        start = monday
    elif grain == "month":
        first = today.replace(day=1)
        buckets = []
        for d in range(1, 32):
            try:
                cur = first.replace(day=d)
            except ValueError:
                break
            n = (d - 1 + first.weekday()) // 7 + 1
            key = cur.isoformat()
            if not buckets or buckets[-1][1] != f"第{n}周":
                buckets.append((key, f"第{n}周"))
        start = first
    else:
        buckets = [(f"{today.year}-{m:02d}", f"{m}月") for m in range(1, 13)]
        start = date(today.year, 1, 1)

    workouts = db.scalars(
        select(Workout).where(Workout.user_id == user.id, Workout.date >= start).order_by(Workout.date)
    ).all()

    idx_of = {b[0]: n for n, b in enumerate(buckets)}
    data = {p: [0.0 for _ in buckets] for p, _, _ in PART_META}
    set_count = {p: 0 for p, _, _ in PART_META}
    used = set()

    for w in workouts:
        d = w.date
        if grain == "week":
            key = d.isoformat()
        elif grain == "month":
            key = d.isoformat()
            n = (d.day - 1 + d.replace(day=1).weekday()) // 7 + 1
            key = next((k for k, l in buckets if l == f"第{n}周"), None)
        else:
            key = f"{d.year}-{d.month:02d}"
        pos = idx_of.get(key)
        if pos is None:
            continue
        for st in w.sets:
            if st.is_warmup:
                continue
            v = vol_of(st)
            if v <= 0:
                continue
            ps = parts_of(st)
            share = v / len(ps)
            for p in ps:
                data[p][pos] += share
                set_count[p] += 1
        used.add(pos)

    series = []
    for p, label, color in PART_META:
        tot = round(sum(data[p]))
        if tot <= 0:
            continue
        series.append({
            "part": p, "label": label, "color": color,
            "data": [round(v) for v in data[p]], "total": tot, "sets": set_count[p],
        })

    return {
        "grain": grain, "mode": "by_time",
        "buckets": [{"key": k, "label": l} for k, l in buckets],
        "series": series,
        "total_volume": round(sum(x["total"] for x in series)),
        "active_buckets": len(used),
    }


@router.get("/strength/heatmap")
def strength_heatmap(
    weeks: int = Query(26, ge=4, le=104),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """训练日历热力图：返回最近 N 周每天的容量，用于 GitHub 风格贡献图。"""
    today = date.today()
    # 对齐到本周周一，向前推 weeks 周
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    workouts = db.scalars(
        select(Workout)
        .where(Workout.user_id == user.id, Workout.date >= start)
        .order_by(Workout.date)
    ).all()

    ex_map = {e.id: e for e in db.scalars(select(Exercise)).all()}

    per_day: dict[str, dict] = {}
    for w in workouts:
        key = w.date.isoformat()
        node = per_day.setdefault(
            key, {"date": key, "volume": 0.0, "sets": 0, "sessions": 0, "names": []}
        )
        node["sessions"] += 1
        if w.name:
            node["names"].append(w.name)
        for st in w.sets:
            if st.is_warmup:
                continue
            node["sets"] += 1
            kg = st.weight_kg or 0.0
            reps = st.reps or 0
            node["volume"] += kg * reps

    days = []
    for k, v in per_day.items():
        v["volume"] = round(v["volume"])
        days.append(v)
    days.sort(key=lambda x: x["date"])
    max_vol = max([d["volume"] for d in days], default=0)
    max_sets = max([d["sets"] for d in days], default=0)

    return {
        "weeks": weeks,
        "start": start.isoformat(),
        "end": today.isoformat(),
        "max_volume": max_vol,
        "max_sets": max_sets,
        "days": days,
    }


@router.put("/workouts/{wid:int}")
def update_workout(
    wid: int,
    body: WorkoutIn,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """整体替换某条训练记录（编辑用）。"""
    w = db.get(Workout, wid)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "记录不存在")
    w.date = body.date
    w.name = body.name
    w.focus = body.focus
    w.duration_min = body.duration_min
    w.rpe = body.rpe
    w.notes = body.notes
    for old in list(w.sets):
        db.delete(old)
    db.flush()
    for i, st in enumerate(body.sets):
        db.add(WorkoutSet(workout_id=w.id, idx=i, **st.model_dump()))
    db.commit()
    return {"ok": True, "id": w.id, "sets": len(body.sets)}


@router.get("/strength/stats")
def strength_stats(
    days: int = Query(7, ge=1, le=365),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=max(days, 56))
    rows = db.scalars(
        select(Workout).where(Workout.user_id == user.id, Workout.date >= cutoff).order_by(Workout.date)
    ).all()
    dicts = [_workout_dict(w) for w in rows]
    cov = strength.muscle_coverage(dicts, days=days)
    return {
        **cov,
        "volume_trend": strength.volume_trend(dicts),
        "records": strength.personal_records(dicts)[:10],
    }


@router.get("/strength/plan")
def get_plan(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    prof = _user_profile(db, user)
    cutoff = date.today() - timedelta(days=7)
    rows = db.scalars(
        select(Workout).where(Workout.user_id == user.id, Workout.date >= cutoff)
    ).all()
    cov = strength.muscle_coverage([_workout_dict(w) for w in rows], days=7)
    weak = [m["muscle"] for m in cov["muscles"] if m["status"] in ("未训练", "不足")]
    return strength.suggest_plan(
        prof["goal"] or "recomp",
        prof["training_days_per_week"] or 4,
        weak_muscles=weak,
    )


# ==========================================================================
# 营养
# ==========================================================================
@router.get("/nutrition/plan")
def nutrition_plan(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    prof = _user_profile(db, user)
    if not prof["weight_kg"] or not prof["height_cm"] or not prof["age"]:
        return {"complete": False, "missing": "需要先填写身高、出生年份，并记录一次体重"}

    cutoff = datetime.now() - timedelta(days=28)
    runs = db.scalars(select(Run).where(Run.user_id == user.id, Run.start_time >= cutoff)).all()
    weekly_km = sum((r.distance_m or 0) for r in runs) / 1000.0 / 4.0

    t = nutrition.tdee(
        prof["sex"] or "male",
        prof["weight_kg"],
        prof["height_cm"],
        prof["age"],
        prof["activity_level"] or "moderate",
        prof["bodyfat_pct"],
        weekly_km,
        prof["training_days_per_week"] or 4,
    )
    weekly = nutrition.weekly_nutrition(
        prof["goal"] or "recomp",
        t["tdee"],
        prof["weight_kg"],
        prof["training_days_per_week"] or 4,
    )
    per = weekly.get("per_day_type") or {}
    return {
        "complete": True,
        "tdee": t,
        "weekly_km": round(weekly_km, 1),
        # 兼容旧前端：把 per_day_type 摊平到顶层
        "plan": {**weekly, **per},
    }


class MealIn(BaseModel):
    date: date
    slot: str | None = None
    description: str | None = None
    kcal: float | None = None
    protein_g: float | None = None
    carb_g: float | None = None
    fat_g: float | None = None


@router.post("/meals")
def add_meal(body: MealIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    m = Meal(user_id=user.id, **body.model_dump())
    db.add(m)
    db.commit()
    return {"ok": True, "id": m.id}


@router.get("/meals")
def list_meals(
    d: date | None = None,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    d = d or date.today()
    rows = db.scalars(
        select(Meal).where(Meal.user_id == user.id, Meal.date == d).order_by(Meal.id)
    ).all()
    total = {
        "kcal": sum(m.kcal or 0 for m in rows),
        "protein_g": sum(m.protein_g or 0 for m in rows),
        "carb_g": sum(m.carb_g or 0 for m in rows),
        "fat_g": sum(m.fat_g or 0 for m in rows),
    }
    # 建议摄入：按当天是否训练取不同 day_type
    target = None
    try:
        plan = nutrition_plan(user=user, db=db)
        if plan.get("complete"):
            wrows = db.scalars(
                select(Workout).where(Workout.user_id == user.id, Workout.date == d)
            ).all()
            rrows = db.scalars(
                select(Run).where(
                    Run.user_id == user.id,
                    func.date(Run.start_time) == d.isoformat(),
                )
            ).all()
            day_type = "training" if wrows else ("long_run" if rrows else "rest")
            # weekly_nutrition 返回 {"per_day_type": {...}, ...}
            tp = plan["plan"].get("per_day_type") or plan["plan"]
            key = "training" if day_type == "training" else ("long_run" if day_type == "long_run" else "rest")
            target = tp.get(key) or tp.get("training")
            if target:
                target = {
                    "day_type": day_type,
                    "kcal": target["kcal"],
                    "protein_g": target["protein_g"],
                    "carb_g": target["carb_g"],
                    "fat_g": target["fat_g"],
                }
    except Exception:
        target = None

    slots_done = sorted({m.slot for m in rows if m.slot})
    return {
        "date": d.isoformat(),
        "items": [
            {"id": m.id, "slot": m.slot, "description": m.description, "kcal": m.kcal,
             "protein_g": m.protein_g, "carb_g": m.carb_g, "fat_g": m.fat_g}
            for m in rows
        ],
        "total": {k: round(v, 1) for k, v in total.items()},
        "target": target,
        "slots_done": slots_done,
        "meals_complete": all(s in slots_done for s in ("breakfast", "lunch", "dinner")),
    }


class MealFromFoodsIn(BaseModel):
    date: date
    slot: str | None = None
    items: list[dict] = Field(default_factory=list)  # [{name, grams}]


@router.post("/meals/from-foods")
def add_meal_from_foods(
    body: MealFromFoodsIn,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """从食物库按克数直接记账。"""
    if not body.items:
        raise HTTPException(400, "没有选择食物")
    names, kcal, p, c, f = [], 0.0, 0.0, 0.0, 0.0
    for it in body.items:
        name = str(it.get("name") or "").strip()
        grams = float(it.get("grams") or 0)
        if not name or grams <= 0:
            continue
        food = next((x for x in foods.FOODS if x["name"] == name), None)
        if not food:
            continue
        n = foods.compute(food, grams)
        names.append(f"{name} {round(grams)}g")
        kcal += n["kcal"]; p += n["protein_g"]; c += n["carb_g"]; f += n["fat_g"]
    if not names:
        raise HTTPException(400, "没有可用的食物条目")

    m = Meal(
        user_id=user.id, date=body.date, slot=body.slot,
        description="、".join(names),
        kcal=round(kcal, 1), protein_g=round(p, 1),
        carb_g=round(c, 1), fat_g=round(f, 1),
    )
    db.add(m)
    db.commit()
    return {"ok": True, "id": m.id}


# ==========================================================================
# 食物库（内置，可按 100g 换算任意克数）
# ==========================================================================
@router.get("/foods/calc")
def calc_food(name: str = Query(...), grams: float = Query(...)):
    """按名称 + 克数换算营养。"""
    hit = None
    for f in foods.FOODS:
        if f["name"] == name:
            hit = f
            break
    if hit is None:
        cands = foods.search(name, 1)
        if not cands:
            raise HTTPException(404, "食物库里没有这个食物")
        hit = cands[0]
    out = foods.compute(hit, grams)
    out["name"] = hit["name"]
    out["grams"] = grams
    return out


@router.delete("/meals/{mid:int}")
def delete_meal(mid: int, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    m = db.get(Meal, mid)
    if not m or m.user_id != user.id:
        raise HTTPException(404, "记录不存在")
    db.delete(m)
    db.commit()
    return {"ok": True}

@router.get("/foods")
def list_foods(q: str = Query(""), limit: int = Query(80, ge=1, le=300)):
    """内置食物库搜索（每 100g 营养），供前端挑选。"""
    items = foods.search(q, limit)
    return {"count": len(items), "items": items}


class FoodCalcIn(BaseModel):
    name: str
    grams: float


@router.post("/foods/calc")
def calc_food(body: FoodCalcIn):
    """按克数换算某个食物的营养（名称需精确匹配食物库）。"""
    for f in foods.FOODS:
        if f["name"] == body.name:
            out = foods.compute(f, body.grams)
            out["name"] = f["name"]
            out["grams"] = body.grams
            return out
    raise HTTPException(404, "食物库中没有这个食物")



# ==========================================================================
# AI 教练
# ==========================================================================
class ChatIn(BaseModel):
    message: str
    module: str = "general"  # general / nutrition / run / strength


def _full_context(db: OrmSession, user: User) -> str:
    prof = _user_profile(db, user)

    cutoff = datetime.now() - timedelta(days=28)
    runs = db.scalars(
        select(Run).where(Run.user_id == user.id, Run.start_time >= cutoff).order_by(Run.start_time)
    ).all()
    run_summary = None
    if runs:
        dicts = [_run_dict(r) for r in runs]
        ws = analytics.weekly_summary(dicts, prof["hr_max"], prof["hr_rest"])
        daily = [(r.start_time.date(), analytics.run_load(_run_dict(r), prof["hr_max"], prof["hr_rest"])) for r in runs]
        run_summary = {
            "近28天": ws,
            "acwr": analytics.acute_chronic_ratio(daily),
            "最近3次": [
                {
                    "date": r.start_time.strftime("%Y-%m-%d"),
                    "km": round((r.distance_m or 0) / 1000, 2),
                    "pace": analytics.pace_str(r.distance_m, r.moving_s or r.duration_s),
                    "avg_hr": r.avg_hr,
                    "cadence": r.avg_cadence,
                    "zone_pct": analytics.analyze_run(_run_dict(r), prof["hr_max"], prof["hr_rest"])["zone_pct"],
                }
                for r in runs[-3:]
            ],
        }

    wcut = date.today() - timedelta(days=28)
    wrows = db.scalars(select(Workout).where(Workout.user_id == user.id, Workout.date >= wcut)).all()
    strength_summary = None
    if wrows:
        dicts = [_workout_dict(w) for w in wrows]
        cov = strength.muscle_coverage(dicts, days=7)
        strength_summary = {
            "近7天肌肉覆盖": [
                {"肌肉": m["name"], "组数": m["sets"], "状态": m["status"]}
                for m in cov["muscles"] if m["sets"] > 0
            ],
            "未训练": cov["neglected"],
            "推拉腿": cov["balance"],
            "容量趋势": strength.volume_trend(dicts),
            "最佳记录": strength.personal_records(dicts)[:5],
        }

    nutrition_summary = None
    if prof["weight_kg"] and prof["height_cm"] and prof["age"]:
        weekly_km = sum((r.distance_m or 0) for r in runs) / 1000.0 / 4.0
        t = nutrition.tdee(
            prof["sex"] or "male", prof["weight_kg"], prof["height_cm"], prof["age"],
            prof["activity_level"] or "moderate", prof["bodyfat_pct"], weekly_km,
            prof["training_days_per_week"] or 4,
        )
        nutrition_summary = {
            "tdee": t,
            "计划": nutrition.weekly_nutrition(
                prof["goal"] or "recomp", t["tdee"], prof["weight_kg"],
                prof["training_days_per_week"] or 4,
            ),
        }
        bms = db.scalars(
            select(BodyMetric).where(BodyMetric.user_id == user.id).order_by(BodyMetric.date)
        ).all()
        if bms:
            nutrition_summary["体重趋势"] = nutrition.weight_trend(
                [(b.date, b.weight_kg) for b in bms if b.weight_kg]
            )

    return llm.build_context(prof, run_summary, strength_summary, nutrition_summary)


@router.post("/coach/chat")
async def coach_chat(body: ChatIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    if not get_cfg(db, user).configured:
        raise HTTPException(400, "尚未配置 AI Key。请到「我的 → AI 设置」填入你自己的 API Key")

    history = db.scalars(
        select(CoachMessage).where(CoachMessage.user_id == user.id).order_by(CoachMessage.id.desc()).limit(10)
    ).all()
    msgs = [{"role": m.role, "content": m.content} for m in reversed(history)]

    ctx = _full_context(db, user)
    msgs.append({"role": "user", "content": f"{ctx}\n\n---\n\n用户提问：{body.message}"})

    reply = await llm.chat(get_cfg(db, user), msgs)

    db.add(CoachMessage(user_id=user.id, role="user", content=body.message, module=body.module))
    db.add(CoachMessage(user_id=user.id, role="assistant", content=reply, module=body.module))
    db.commit()
    return {"reply": reply}


@router.post("/coach/stream")
async def coach_stream(body: ChatIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    if not get_cfg(db, user).configured:
        raise HTTPException(400, "尚未配置 DeepSeek API Key")

    history = db.scalars(
        select(CoachMessage).where(CoachMessage.user_id == user.id).order_by(CoachMessage.id.desc()).limit(10)
    ).all()
    msgs = [{"role": m.role, "content": m.content} for m in reversed(history)]
    ctx = _full_context(db, user)
    msgs.append({"role": "user", "content": f"{ctx}\n\n---\n\n用户提问：{body.message}"})

    db.add(CoachMessage(user_id=user.id, role="user", content=body.message, module=body.module))
    db.commit()

    async def gen():
        buf = []
        try:
            async for delta in llm.chat_stream(get_cfg(db, user), msgs):
                buf.append(delta)
                yield delta
        except Exception as exc:  # noqa: BLE001
            yield f"\n\n[出错: {exc}]"
        finally:
            if buf:
                from .db import SessionLocal

                s = SessionLocal()
                s.add(CoachMessage(user_id=user.id, role="assistant", content="".join(buf), module=body.module))
                s.commit()
                s.close()

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


@router.get("/coach/history")
def coach_history(
    limit: int = Query(50, ge=1, le=500),
    module: str | None = None,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    stmt = select(CoachMessage).where(CoachMessage.user_id == user.id)
    if module:
        stmt = stmt.where(CoachMessage.module == module)
    rows = db.scalars(stmt.order_by(CoachMessage.id.desc()).limit(limit)).all()
    return {
        "items": [
            {"id": m.id, "role": m.role, "content": m.content, "module": m.module,
             "at": m.created_at.isoformat() if m.created_at else None}
            for m in reversed(rows)
        ]
    }


@router.get("/coach/review")
def coach_review_data(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    """给「周复盘」按钮用的聚合数据（不调 LLM）。"""
    return {"context": _full_context(db, user)}


# ==========================================================================
# Apple 健康数据导入（export.xml）
# ==========================================================================
@router.post("/health/import")
async def import_apple_health(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """导入 Apple 健康 export.xml：训练记录 + 体重/体脂/静息心率/睡眠。"""
    name = file.filename or "export.xml"
    if not name.lower().endswith(".xml"):
        raise HTTPException(400, "请上传 export.xml")

    dest = settings.UPLOAD_DIR / f"health_{uuid.uuid4().hex}.xml"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)

    try:
        data = parsers.parse_apple_export(dest)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"解析失败：{exc}")

    # 1) 训练记录 -> runs
    runs_added = 0
    for w in data.get("workouts", []):
        pr = _apple_workout_to_parsed(w)
        if pr and _save_parsed(db, user.id, pr, name):
            runs_added += 1

    # 2) 身体指标 -> body_metrics（按天 upsert，只填空缺，不覆盖手填）
    body_added, body_updated = 0, 0
    for day_str, vals in (data.get("body_metrics") or {}).items():
        try:
            d = date.fromisoformat(day_str)
        except ValueError:
            continue
        row = db.scalars(
            select(BodyMetric).where(BodyMetric.user_id == user.id, BodyMetric.date == d)
        ).first()
        if row is None:
            row = BodyMetric(user_id=user.id, date=d)
            db.add(row)
            body_added += 1
        else:
            body_updated += 1
        for k, v in vals.items():
            if hasattr(row, k) and v is not None:
                setattr(row, k, v)

    db.commit()
    return {
        "ok": True,
        "runs_imported": runs_added,
        "body_days_added": body_added,
        "body_days_updated": body_updated,
        "metrics": sorted(list((data.get("body_metrics") or {}).keys()))[:0] or None,
    }


def _apple_workout_to_parsed(w: dict):
    """把 Apple Health 的 workout dict 转成 ParsedRun。"""
    try:
        start = w.get("start")
        dur = w.get("duration_s")
        if not start or not dur:
            return None
        dist = w.get("distance_m") or 0
        ext = "apple:" + start.isoformat()
        return parsers.ParsedRun(
            start_time=start,
            activity_type=parsers._map_sport(w.get("sport") or "other"),
            name=w.get("sport"),
            distance_m=float(dist) if dist else 0.0,
            duration_s=float(dur),
            moving_s=None,
            avg_hr=None, max_hr=None, avg_cadence=None,
            elevation_gain_m=None, calories=w.get("energy_kcal"),
            samples=[], splits=[],
            source="apple_health",
            external_id=ext,
        )
    except Exception:  # noqa: BLE001
        return None


# ==========================================================================
# 仪表盘
# ==========================================================================
@router.get("/dashboard")
def dashboard(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    prof = _user_profile(db, user)
    today = date.today()
    week_ago = today - timedelta(days=7)

    runs_7 = db.scalars(
        select(Run).where(
            Run.user_id == user.id,
            Run.start_time >= datetime.combine(week_ago, datetime.min.time()),
        )
    ).all()
    wk_7 = db.scalars(
        select(Workout).where(Workout.user_id == user.id, Workout.date >= week_ago)
    ).all()
    bm = db.scalars(
        select(BodyMetric).where(BodyMetric.user_id == user.id).order_by(BodyMetric.date.desc()).limit(1)
    ).first()

    return {
        "profile": prof,
        "week": {
            "runs": len(runs_7),
            "run_km": round(sum((r.distance_m or 0) for r in runs_7) / 1000, 1),
            "strength_sessions": len(wk_7),
            "strength_sets": sum(
                1 for w in wk_7 for s in w.sets if not s.is_warmup
            ),
        },
        "latest": {
            "weight_kg": bm.weight_kg if bm else None,
            "bodyfat_pct": bm.bodyfat_pct if bm else None,
            "date": bm.date.isoformat() if bm else None,
        },
        "llm_configured": get_cfg(db, user).configured,
        "llm_own": has_own_cfg(db, user),
    }


# ==========================================================================
# 训练模板（三分化：只改配重）
# ==========================================================================
def _template_dict(t: WorkoutTemplate, last_weights: dict[int, dict] | None = None) -> dict:
    items = []
    for it in t.items:
        prev = (last_weights or {}).get(it.exercise_id)
        items.append(
            {
                "id": it.id,
                "exercise_id": it.exercise_id,
                "exercise_name": it.exercise.name if it.exercise else None,
                "primary_muscles": it.exercise.primary_muscles if it.exercise else "[]",
                "sets": it.sets,
                "reps": it.reps,
                "rest_s": it.rest_s,
                "target_weight_kg": it.target_weight_kg,
                "note": it.note,
                "last_weight_kg": prev["weight_kg"] if prev else None,
                "last_rpe": prev["rpe"] if prev else None,
                "last_date": prev["date"] if prev else None,
            }
        )
    return {
        "id": t.id,
        "name": t.name,
        "focus": t.focus,
        "note": t.note,
        "is_builtin": t.is_builtin,
        "items": items,
    }


def _last_weights_by_exercise(db: OrmSession, user_id: int, exercise_ids: list[int]) -> dict[int, dict]:
    """每个动作最近一次的重量/RPE，方便模板预填。"""
    if not exercise_ids:
        return {}
    rows = (
        db.query(WorkoutSet, Workout)
        .join(Workout, WorkoutSet.workout_id == Workout.id)
        .filter(Workout.user_id == user_id, WorkoutSet.exercise_id.in_(exercise_ids))
        .order_by(Workout.date.desc(), WorkoutSet.idx)
        .all()
    )
    out: dict[int, dict] = {}
    for s, w in rows:
        if s.exercise_id not in out and s.weight_kg is not None:
            out[s.exercise_id] = {
                "weight_kg": s.weight_kg,
                "rpe": s.rpe,
                "date": w.date.isoformat(),
            }
    return out


@router.get("/templates")
def list_templates(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    rows = db.scalars(
        select(WorkoutTemplate)
        .where((WorkoutTemplate.user_id == None) | (WorkoutTemplate.user_id == user.id))  # noqa: E711
        .order_by(WorkoutTemplate.sort_order, WorkoutTemplate.id)
    ).all()
    ex_ids = [it.exercise_id for t in rows for it in t.items]
    last = _last_weights_by_exercise(db, user.id, ex_ids)
    return {"items": [_template_dict(t, last) for t in rows]}


@router.get("/templates/{tid:int}")
def get_template(tid: int, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    t = db.get(WorkoutTemplate, tid)
    if not t or (t.user_id is not None and t.user_id != user.id):
        raise HTTPException(404, "模板不存在")
    last = _last_weights_by_exercise(db, user.id, [it.exercise_id for it in t.items])
    return _template_dict(t, last)


class TemplateItemIn(BaseModel):
    exercise_id: int
    sets: int | None = None
    reps: str | None = None
    rest_s: int | None = None
    target_weight_kg: float | None = None
    note: str | None = None


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    focus: str | None = None
    note: str | None = None
    items: list[TemplateItemIn] = []


@router.post("/templates")
def create_template(body: TemplateIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    t = WorkoutTemplate(user_id=user.id, name=body.name, focus=body.focus, note=body.note, is_builtin=False)
    db.add(t)
    db.flush()
    for i, it in enumerate(body.items):
        db.add(TemplateItem(template_id=t.id, idx=i, **it.model_dump()))
    db.commit()
    return {"ok": True, "id": t.id}


def _clone_template(db: OrmSession, t: WorkoutTemplate, user_id: int, name: str | None = None) -> WorkoutTemplate:
    """把模板（可能是内置的）复制一份归到用户名下。"""
    nt = WorkoutTemplate(
        user_id=user_id,
        name=name or t.name,
        focus=t.focus,
        note=t.note,
        is_builtin=False,
        sort_order=t.sort_order,
    )
    db.add(nt)
    db.flush()
    for it in t.items:
        db.add(
            TemplateItem(
                template_id=nt.id,
                exercise_id=it.exercise_id,
                idx=it.idx,
                sets=it.sets,
                reps=it.reps,
                rest_s=it.rest_s,
                target_weight_kg=it.target_weight_kg,
                note=it.note,
            )
        )
    db.flush()
    return nt


@router.put("/templates/{tid:int}")
def update_template(
    tid: int,
    body: TemplateIn,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """全量更新计划。内置模板会先克隆成用户自己的副本再改，避免破坏内置数据。"""
    t = db.get(WorkoutTemplate, tid)
    if not t or (t.user_id is not None and t.user_id != user.id):
        raise HTTPException(404, "模板不存在")
    cloned = False
    if t.user_id is None:
        t = _clone_template(db, t, user.id, body.name)
        cloned = True
    t.name = body.name
    t.focus = body.focus
    t.note = body.note
    t.items.clear()
    db.flush()
    for i, it in enumerate(body.items):
        db.add(TemplateItem(template_id=t.id, idx=i, **it.model_dump()))
    db.commit()
    return {"ok": True, "id": t.id, "cloned": cloned}


@router.post("/templates/{tid:int}/duplicate")
def duplicate_template(
    tid: int,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    t = db.get(WorkoutTemplate, tid)
    if not t or (t.user_id is not None and t.user_id != user.id):
        raise HTTPException(404, "模板不存在")
    nt = _clone_template(db, t, user.id, f"{t.name} 副本")
    db.commit()
    return {"ok": True, "id": nt.id}


@router.delete("/templates/{tid:int}")
def delete_template(tid: int, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    """删除模板。内置模板也可删除——删掉后不会再自动重建。"""
    t = db.get(WorkoutTemplate, tid)
    if not t:
        raise HTTPException(404, "模板不存在")
    if t.user_id is not None and t.user_id != user.id:
        raise HTTPException(403, "无权删除他人的模板")
    db.delete(t)
    db.commit()
    return {"ok": True, "builtin": bool(t.is_builtin)}


class FromTemplateIn(BaseModel):
    date: date
    weights: dict[int, float] = {}   # exercise_id -> weight_kg
    rpes: dict[int, float] = {}
    duration_min: float | None = None
    notes: str | None = None


@router.post("/templates/{tid:int}/log")
def log_from_template(
    tid: int,
    body: FromTemplateIn,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """用模板一键生成当天训练记录：动作/组数来自模板，重量/RPE 来自用户输入。"""
    t = db.get(WorkoutTemplate, tid)
    if not t or (t.user_id is not None and t.user_id != user.id):
        raise HTTPException(404, "模板不存在")

    # 同一天、同一计划：覆盖式保存（不叠加）
    existing = db.scalars(
        select(Workout).where(
            Workout.user_id == user.id,
            Workout.date == body.date,
            Workout.name == t.name,
        )
    ).all()
    replaced_id = None
    for old_w in existing:
        replaced_id = old_w.id
        db.delete(old_w)   # cascade 删除 sets
    db.flush()

    w = Workout(
        user_id=user.id,
        date=body.date,
        name=t.name,
        focus=t.focus,
        duration_min=body.duration_min,
        notes=body.notes,
    )
    db.add(w)
    db.flush()

    idx = 0
    for it in t.items:
        # 优先用本次填写的重量，否则回退到计划里预设的重量
        weight = body.weights.get(it.exercise_id)
        if weight is None:
            weight = it.target_weight_kg
        rpe = body.rpes.get(it.exercise_id)
        n_sets = it.sets or 3
        for _ in range(n_sets):
            db.add(
                WorkoutSet(
                    workout_id=w.id,
                    exercise_id=it.exercise_id,
                    idx=idx,
                    reps=_parse_reps_mid(it.reps),
                    weight_kg=weight,
                    rpe=rpe,
                    rest_s=it.rest_s,
                )
            )
            idx += 1
    db.commit()
    return {"ok": True, "id": w.id, "sets": idx, "replaced": replaced_id}


def _parse_reps_mid(reps: str | None) -> int | None:
    if not reps:
        return None
    nums = [int(x) for x in __import__("re").findall(r"\d+", reps)]
    if not nums:
        return None
    return sum(nums) // len(nums)


# ==========================================================================
# 拍照识餐
# ==========================================================================
# ==========================================================================
# 食物库（按 100g 记录营养，按份量换算）
# ==========================================================================
@router.post("/meals/photo")
async def meal_photo(
    file: UploadFile = File(...),
    note: str = Query(""),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """上传餐食照片 → 视觉模型识别 → 返回结构化宏量（不落库，用户确认后再保存）。"""
    if not get_cfg(db, user).configured:
        raise HTTPException(400, "尚未配置 DeepSeek API Key")

    raw = await file.read()
    if len(raw) > 12 * 1024 * 1024:
        raise HTTPException(400, "图片太大，请压缩到 12MB 以内")

    suffix = Path(file.filename or "meal.jpg").suffix.lower() or ".jpg"
    dest = settings.MEAL_IMG_DIR / f"{uuid.uuid4().hex}{suffix}"
    dest.write_bytes(raw)

    mime = "image/png" if suffix == ".png" else "image/jpeg"
    b64 = base64.b64encode(raw).decode()
    try:
        result = await llm.analyze_meal_image(get_cfg(db, user), b64, mime=mime, note=note)
    except llm.LLMNotConfigured as exc:
        raise HTTPException(400, "还没配置 AI Key，请到「我的→设置→AI 设置」填入 API Key") from exc
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "401" in msg or "Unauthorized" in msg or "invalid_api_key" in msg:
            raise HTTPException(400, "AI Key 无效或已过期，请到「我的→设置→AI 设置」重新填写") from exc
        if "timeout" in msg.lower() or "timed out" in msg.lower():
            raise HTTPException(504, "识别超时，请换一张更小的照片或稍后重试") from exc
        raise HTTPException(500, f"识别失败（服务器）：{msg[:200]}") from exc

    items = result.get("items") or []
    total = {
        "kcal": round(sum(float(i.get("kcal") or 0) for i in items), 1),
        "protein_g": round(sum(float(i.get("protein_g") or 0) for i in items), 1),
        "carb_g": round(sum(float(i.get("carb_g") or 0) for i in items), 1),
        "fat_g": round(sum(float(i.get("fat_g") or 0) for i in items), 1),
    }
    return {
        "items": items,
        "total": total,
        "confidence": result.get("confidence", "medium"),
        "note": result.get("note", ""),
        "image": dest.name,
    }

# ==========================================================================
# 用户自己的 AI 配置
# ==========================================================================
class LlmCfgIn(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    vision_model: str | None = None


def _mask(k: str | None) -> str:
    if not k:
        return ""
    if len(k) <= 8:
        return "*" * len(k)
    return k[:4] + "*" * (len(k) - 8) + k[-4:]


@router.get("/settings/llm")
def get_llm_settings(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    from .models import UserLlmConfig
    row = db.get(UserLlmConfig, user.id)
    cfg = get_cfg(db, user)
    return {
        "own": bool(row and row.api_key),
        "api_key_masked": _mask(row.api_key) if row else "",
        "base_url": (row.base_url if row and row.base_url else cfg.base_url),
        "model": (row.model if row and row.model else cfg.model),
        "vision_model": (row.vision_model if row and row.vision_model else cfg.vision_model),
        "configured": cfg.configured,
        "is_owner": is_owner(db, user),
        "fallback_available": is_owner(db, user) and bool(settings.LLM_API_KEY),
        "defaults": {
            "base_url": settings.LLM_BASE_URL.rstrip("/"),
            "model": settings.LLM_MODEL,
            "vision_model": settings.LLM_VISION_MODEL,
        },
    }


@router.put("/settings/llm")
def put_llm_settings(
    body: LlmCfgIn,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    from .models import UserLlmConfig
    row = db.get(UserLlmConfig, user.id)
    if row is None:
        row = UserLlmConfig(user_id=user.id)
        db.add(row)
    if body.api_key is not None:
        row.api_key = body.api_key.strip() or None
    if body.base_url is not None:
        row.base_url = body.base_url.strip() or None
    if body.model is not None:
        row.model = body.model.strip() or None
    if body.vision_model is not None:
        row.vision_model = body.vision_model.strip() or None
    db.commit()
    return {"ok": True, "configured": bool(row.api_key)}


@router.delete("/settings/llm")
def delete_llm_settings(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    from .models import UserLlmConfig
    row = db.get(UserLlmConfig, user.id)
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}


@router.post("/settings/llm/test")
async def test_llm_settings(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    cfg = get_cfg(db, user)
    if not cfg.configured:
        raise HTTPException(400, "还没有配置 API Key")
    try:
        reply = await llm.chat(cfg, [{"role": "user", "content": "只回复两个字：可用"}], max_tokens=20)
        return {"ok": True, "reply": (reply or "").strip()[:50]}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"调用失败：{exc}") from exc


# ==========================================================================
# 身体数据趋势（按指标分别返回序列）
# ==========================================================================
@router.get("/body/trends")
def body_trends(
    days: int = Query(365, ge=7, le=3650),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=days)
    rows = db.scalars(
        select(BodyMetric)
        .where(BodyMetric.user_id == user.id, BodyMetric.date >= cutoff)
        .order_by(BodyMetric.date)
    ).all()

    metrics = {
        "weight_kg": {"label": "体重", "unit": "kg"},
        "bodyfat_pct": {"label": "体脂率", "unit": "%"},
        "muscle_kg": {"label": "肌肉量", "unit": "kg"},
        "waist_cm": {"label": "腰围", "unit": "cm"},
        "hip_cm": {"label": "臀围", "unit": "cm"},
        "chest_cm": {"label": "胸围", "unit": "cm"},
        "arm_cm": {"label": "臂围", "unit": "cm"},
        "thigh_cm": {"label": "腿围", "unit": "cm"},
        "resting_hr": {"label": "静息心率", "unit": "bpm"},
        "sleep_hours": {"label": "睡眠", "unit": "h"},
    }

    out = {}
    for key, meta in metrics.items():
        series = []
        for r in rows:
            v = getattr(r, key, None)
            if v is not None:
                series.append({"date": r.date.isoformat(), "value": float(v)})
        if series:
            vals = [p["value"] for p in series]
            out[key] = {
                **meta,
                "series": series,
                "count": len(series),
                "first": vals[0],
                "last": vals[-1],
                "min": min(vals),
                "max": max(vals),
                "avg": round(sum(vals) / len(vals), 2),
                "delta": round(vals[-1] - vals[0], 2),
            }
    return {"days": days, "metrics": out, "available": list(out.keys())}