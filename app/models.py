"""ORM 模型。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # --- 身体基础 ---
    sex: Mapped[str | None] = mapped_column(String(8))            # male / female
    birth_year: Mapped[int | None] = mapped_column(Integer)
    height_cm: Mapped[float | None] = mapped_column(Float)
    target_weight_kg: Mapped[float | None] = mapped_column(Float)
    target_bodyfat_pct: Mapped[float | None] = mapped_column(Float)
    goal: Mapped[str | None] = mapped_column(String(32))          # recomp / cut / bulk / run
    activity_level: Mapped[str | None] = mapped_column(String(32))  # sedentary/light/moderate/active
    training_days_per_week: Mapped[int | None] = mapped_column(Integer)
    diet_notes: Mapped[str | None] = mapped_column(Text)
    injury_notes: Mapped[str | None] = mapped_column(Text)
    focus_muscles: Mapped[str | None] = mapped_column(Text)       # JSON list
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    # 自动同步令牌：供 Health Auto Export / 快捷指令 / Health Connect 桥接写入数据
    sync_token: Mapped[str | None] = mapped_column(String(96), index=True)


class Session(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class BodyMetric(Base):
    __tablename__ = "body_metrics"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_body_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    bodyfat_pct: Mapped[float | None] = mapped_column(Float)
    muscle_kg: Mapped[float | None] = mapped_column(Float)
    waist_cm: Mapped[float | None] = mapped_column(Float)
    hip_cm: Mapped[float | None] = mapped_column(Float)
    chest_cm: Mapped[float | None] = mapped_column(Float)
    arm_cm: Mapped[float | None] = mapped_column(Float)
    thigh_cm: Mapped[float | None] = mapped_column(Float)
    resting_hr: Mapped[float | None] = mapped_column(Float)
    sleep_hours: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text)


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    name_en: Mapped[str | None] = mapped_column(String(128))
    primary_muscles: Mapped[str] = mapped_column(Text, default="[]")   # JSON
    secondary_muscles: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    equipment: Mapped[str | None] = mapped_column(String(48))
    category: Mapped[str | None] = mapped_column(String(32))  # push/pull/legs/core/cardio
    is_compound: Mapped[bool] = mapped_column(Boolean, default=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    notes: Mapped[str | None] = mapped_column(Text)


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    focus: Mapped[str | None] = mapped_column(String(64))       # push/pull/legs/upper/lower/full
    duration_min: Mapped[float | None] = mapped_column(Float)
    rpe: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan", order_by="WorkoutSet.idx"
    )


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    idx: Mapped[int] = mapped_column(Integer, default=0)
    reps: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    rpe: Mapped[float | None] = mapped_column(Float)
    is_warmup: Mapped[bool] = mapped_column(Boolean, default=False)
    rest_s: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)

    workout: Mapped[Workout] = relationship(back_populates="sets")
    exercise: Mapped[Exercise] = relationship()


class WorkoutTemplate(Base):
    """训练模板：三分化（推/拉/腿）固定动作，每次只改重量。"""

    __tablename__ = "workout_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))            # 推日 / 拉日 / 腿日
    focus: Mapped[str | None] = mapped_column(String(64))    # push/pull/legs
    note: Mapped[str | None] = mapped_column(Text)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["TemplateItem"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="TemplateItem.idx"
    )


class TemplateItem(Base):
    __tablename__ = "template_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("workout_templates.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    idx: Mapped[int] = mapped_column(Integer, default=0)
    sets: Mapped[int | None] = mapped_column(Integer)        # 计划组数
    reps: Mapped[str | None] = mapped_column(String(16))     # "8-12" 允许区间
    rest_s: Mapped[int | None] = mapped_column(Integer)
    target_weight_kg: Mapped[float | None] = mapped_column(Float)  # 计划预设重量
    note: Mapped[str | None] = mapped_column(Text)

    template: Mapped[WorkoutTemplate] = relationship(back_populates="items")
    exercise: Mapped[Exercise] = relationship()


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    activity_type: Mapped[str] = mapped_column(String(32), default="running")
    name: Mapped[str | None] = mapped_column(String(128))
    distance_m: Mapped[float | None] = mapped_column(Float)
    duration_s: Mapped[float | None] = mapped_column(Float)
    moving_s: Mapped[float | None] = mapped_column(Float)
    avg_hr: Mapped[float | None] = mapped_column(Float)
    max_hr: Mapped[float | None] = mapped_column(Float)
    avg_cadence: Mapped[float | None] = mapped_column(Float)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float)
    calories: Mapped[float | None] = mapped_column(Float)
    avg_power: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(32))       # tcx/gpx/csv/apple/manual
    source_file: Mapped[str | None] = mapped_column(String(255))
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)
    samples_json: Mapped[str | None] = mapped_column(Text)       # [[t,hr,cad,speed,elev], ...]
    splits_json: Mapped[str | None] = mapped_column(Text)        # 每公里分段
    raw_meta: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NutritionDay(Base):
    __tablename__ = "nutrition_days"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_nutri_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    day_type: Mapped[str | None] = mapped_column(String(16))     # training / rest / long_run
    target_kcal: Mapped[float | None] = mapped_column(Float)
    target_protein_g: Mapped[float | None] = mapped_column(Float)
    target_carb_g: Mapped[float | None] = mapped_column(Float)
    target_fat_g: Mapped[float | None] = mapped_column(Float)
    actual_kcal: Mapped[float | None] = mapped_column(Float)
    actual_protein_g: Mapped[float | None] = mapped_column(Float)
    actual_carb_g: Mapped[float | None] = mapped_column(Float)
    actual_fat_g: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    slot: Mapped[str | None] = mapped_column(String(16))          # breakfast/lunch/dinner/snack
    description: Mapped[str | None] = mapped_column(Text)
    kcal: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    carb_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PlanWeek(Base):
    __tablename__ = "plan_weeks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    content_json: Mapped[str] = mapped_column(Text, default="{}")
    generated_by: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CoachMessage(Base):
    __tablename__ = "coach_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))                # user / assistant / system
    content: Mapped[str] = mapped_column(Text)
    module: Mapped[str | None] = mapped_column(String(16))       # nutrition / run / strength / general
    context_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
class WebauthnCredential(Base):
    """Passkey / WebAuthn 凭证。"""
    __tablename__ = "webauthn_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    credential_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    public_key: Mapped[str] = mapped_column(Text)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports: Mapped[str | None] = mapped_column(String(128))
    name: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
class UserLlmConfig(Base):
    """每个用户自己的 AI 配置。不填则 AI 功能不可用。"""
    __tablename__ = "user_llm_configs"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    api_key: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(String(256))
    model: Mapped[str | None] = mapped_column(String(64))
    vision_model: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class HealthSample(Base):
    """通用健康指标存储：任何指标都能收，不丢数据。"""
    __tablename__ = "health_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    metric: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
