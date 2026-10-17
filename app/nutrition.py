"""营养计算：TDEE、宏量分配、训练日/休息日策略。"""
from __future__ import annotations

from datetime import date

ACTIVITY_FACTOR = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


def bmr_mifflin(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    if sex == "female":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5


def katch_mccardle(weight_kg: float, bodyfat_pct: float) -> float:
    lbm = weight_kg * (1 - bodyfat_pct / 100.0)
    return 370 + 21.6 * lbm


def tdee(
    sex: str,
    weight_kg: float,
    height_cm: float,
    age: int,
    activity: str = "moderate",
    bodyfat_pct: float | None = None,
    weekly_run_km: float = 0.0,
    weekly_strength_sessions: int = 0,
) -> dict:
    bmr = bmr_mifflin(sex, weight_kg, height_cm, age)
    if bodyfat_pct:
        bmr = (bmr + katch_mccardle(weight_kg, bodyfat_pct)) / 2.0
    base = bmr * ACTIVITY_FACTOR.get(activity, 1.55)
    # 额外训练消耗
    run_kcal = weekly_run_km * weight_kg * 1.03 / 7.0   # 约 1.03 kcal/kg/km
    strength_kcal = weekly_strength_sessions * 250 / 7.0
    total = base + run_kcal + strength_kcal
    return {
        "bmr": round(bmr),
        "base_tdee": round(base),
        "run_kcal": round(run_kcal),
        "strength_kcal": round(strength_kcal),
        "tdee": round(total),
    }


def macro_plan(
    goal: str,
    tdee_kcal: float,
    weight_kg: float,
    day_type: str = "training",
    bodyfat_pct: float | None = None,
) -> dict:
    """按目标分配热量与宏量。

    goal: recomp(减脂增肌) / cut / bulk / maintain
    day_type: training / rest / long_run
    """
    # 热量调整
    if goal == "cut":
        adj = -0.20 if day_type != "long_run" else -0.10
    elif goal == "bulk":
        adj = 0.12 if day_type != "long_run" else 0.05
    elif goal == "recomp":
        adj = -0.10 if day_type != "long_run" else 0.0
    else:
        adj = 0.0

    kcal = tdee_kcal * (1 + adj)
    # 蛋白：减脂期更高
    protein_per_kg = 2.2 if goal in ("cut", "recomp") else 1.8
    protein_g = weight_kg * protein_per_kg
    # 脂肪：不低于 0.8 g/kg
    fat_g = max(weight_kg * 0.9, kcal * 0.25 / 9.0)
    # 碳水填充
    carb_g = max(0.0, (kcal - protein_g * 4 - fat_g * 9) / 4.0)

    # 训练日碳水后置/加量
    if day_type == "training":
        carb_g *= 1.10
        fat_g *= 0.92
    elif day_type == "long_run":
        carb_g *= 1.25
        fat_g *= 0.88
    elif day_type == "rest":
        carb_g *= 0.85
        fat_g *= 1.08

    kcal = protein_g * 4 + carb_g * 4 + fat_g * 9
    return {
        "day_type": day_type,
        "goal": goal,
        "kcal": round(kcal),
        "protein_g": round(protein_g),
        "carb_g": round(carb_g),
        "fat_g": round(fat_g),
        "protein_kcal_pct": round(protein_g * 4 / kcal * 100, 1) if kcal else 0,
        "carb_kcal_pct": round(carb_g * 4 / kcal * 100, 1) if kcal else 0,
        "fat_kcal_pct": round(fat_g * 9 / kcal * 100, 1) if kcal else 0,
        "protein_per_kg": round(protein_g / weight_kg, 2) if weight_kg else 0,
    }


def weekly_nutrition(
    goal: str,
    tdee_kcal: float,
    weight_kg: float,
    training_days: int,
    run_days: int = 3,
    bodyfat_pct: float | None = None,
) -> dict:
    plan = {}
    for t in ("training", "rest", "long_run"):
        plan[t] = macro_plan(goal, tdee_kcal, weight_kg, t, bodyfat_pct)
    # 周平均
    days = {"training": training_days, "rest": max(0, 7 - training_days - 1), "long_run": 1}
    avg_kcal = sum(plan[k]["kcal"] * days[k] for k in days) / 7.0
    avg_protein = sum(plan[k]["protein_g"] * days[k] for k in days) / 7.0
    return {
        "per_day_type": plan,
        "weekly_avg_kcal": round(avg_kcal),
        "weekly_avg_protein": round(avg_protein),
        "estimated_weekly_delta": round((avg_kcal - tdee_kcal) * 7),
    }


def weight_trend(points: list[tuple[date, float]]) -> dict:
    """线性回归求周均变化速率。"""
    pts = [(d, w) for d, w in points if w]
    if len(pts) < 2:
        return {"rate_per_week": 0.0, "trend": "数据不足"}
    pts.sort(key=lambda x: x[0])
    d0 = pts[0][0]
    xs = [(d - d0).days for d, _ in pts]
    ys = [w for _, w in pts]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return {"rate_per_week": 0.0, "trend": "数据不足"}
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    rate = slope * 7
    if rate < -0.5:
        trend = "下降过快，注意肌肉流失"
    elif rate < -0.15:
        trend = "稳定减脂"
    elif rate <= 0.15:
        trend = "体重稳定（重组期常见）"
    elif rate <= 0.5:
        trend = "缓慢增重"
    else:
        trend = "增重过快，脂肪占比可能偏高"
    return {
        "rate_per_week": round(rate, 3),
        "trend": trend,
        "first": pts[0][1],
        "last": pts[-1][1],
        "days": (pts[-1][0] - d0).days,
    }