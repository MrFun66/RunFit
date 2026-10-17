"""力量训练分析：肌肉覆盖、容量、平衡、计划生成。"""
from __future__ import annotations

import json
from datetime import date, timedelta

MUSCLE_CN = {
    "chest": "胸",
    "front_delt": "前束",
    "side_delt": "中束",
    "rear_delt": "后束",
    "triceps": "三头",
    "biceps": "二头",
    "forearm": "小臂",
    "traps": "斜方",
    "lats": "背阔",
    "mid_back": "中背",
    "lower_back": "下背",
    "abs": "腹",
    "obliques": "腹斜",
    "glutes": "臀",
    "quads": "股四",
    "hamstrings": "腘绳",
    "calves": "小腿",
    "hip_flexor": "髂腰",
}

# 推拉腿平衡分组
PUSH = {"chest", "front_delt", "side_delt", "triceps"}
PULL = {"lats", "mid_back", "rear_delt", "biceps", "traps"}
LEGS = {"quads", "hamstrings", "glutes", "calves"}

# 每周建议组数（MEV 下限 / MAV 理想 / MRV 上限）
WEEKLY_SET_TARGET = {
    "chest": (8, 14, 20),
    "front_delt": (6, 10, 16),
    "side_delt": (8, 16, 24),
    "rear_delt": (8, 16, 24),
    "triceps": (6, 12, 18),
    "biceps": (6, 12, 18),
    "lats": (8, 14, 20),
    "mid_back": (8, 14, 20),
    "traps": (4, 10, 16),
    "lower_back": (4, 8, 12),
    "quads": (8, 14, 20),
    "hamstrings": (6, 12, 18),
    "glutes": (6, 14, 20),
    "calves": (6, 12, 18),
    "abs": (6, 12, 20),
    "obliques": (4, 8, 12),
    "forearm": (2, 6, 10),
}


def _loads(s: str | None) -> list[str]:
    try:
        v = json.loads(s or "[]")
        return v if isinstance(v, list) else []
    except json.JSONDecodeError:
        return []


def muscle_coverage(workouts: list[dict], days: int = 7) -> dict:
    """统计时间窗内每块肌肉的有效组数。"""
    cutoff = date.today() - timedelta(days=days)
    sets_by_muscle: dict[str, float] = {}
    volume_by_muscle: dict[str, float] = {}
    for w in workouts:
        wd = w["date"]
        if isinstance(wd, str):
            wd = date.fromisoformat(wd)
        if wd < cutoff:
            continue
        for s in w["sets"]:
            if s.get("is_warmup"):
                continue
            primary = _loads(s.get("primary_muscles"))
            secondary = _loads(s.get("secondary_muscles"))
            weight = s.get("weight_kg") or 0
            reps = s.get("reps") or 0
            vol = weight * reps
            for m in primary:
                sets_by_muscle[m] = sets_by_muscle.get(m, 0) + 1.0
                volume_by_muscle[m] = volume_by_muscle.get(m, 0) + vol
            for m in secondary:
                sets_by_muscle[m] = sets_by_muscle.get(m, 0) + 0.5
                volume_by_muscle[m] = volume_by_muscle.get(m, 0) + vol * 0.5

    rows = []
    for m, (mev, mav, mrv) in WEEKLY_SET_TARGET.items():
        got = round(sets_by_muscle.get(m, 0), 1)
        if got == 0:
            status, color = "未训练", "gray"
        elif got < mev:
            status, color = "不足", "orange"
        elif got <= mav:
            status, color = "达标", "green"
        elif got <= mrv:
            status, color = "充足", "blue"
        else:
            status, color = "过量", "red"
        rows.append(
            {
                "muscle": m,
                "name": MUSCLE_CN.get(m, m),
                "sets": got,
                "volume_kg": round(volume_by_muscle.get(m, 0)),
                "mev": mev,
                "mav": mav,
                "mrv": mrv,
                "status": status,
                "color": color,
            }
        )

    push_sets = sum(sets_by_muscle.get(m, 0) for m in PUSH)
    pull_sets = sum(sets_by_muscle.get(m, 0) for m in PULL)
    leg_sets = sum(sets_by_muscle.get(m, 0) for m in LEGS)

    return {
        "window_days": days,
        "muscles": rows,
        "balance": {
            "push": round(push_sets, 1),
            "pull": round(pull_sets, 1),
            "legs": round(leg_sets, 1),
            "push_pull_ratio": round(push_sets / pull_sets, 2) if pull_sets else 0,
            "note": _balance_note(push_sets, pull_sets, leg_sets),
        },
        "neglected": [r["name"] for r in rows if r["sets"] == 0],
    }


def _balance_note(push: float, pull: float, legs: float) -> str:
    notes = []
    if pull == 0 and push > 0:
        notes.append("完全没有拉类训练，圆肩和肩关节风险会明显上升")
    elif push > pull * 1.3:
        notes.append(f"推 {push:.1f} 组 vs 拉 {pull:.1f} 组，拉类偏少，建议补 2-3 组划船/面拉")
    elif pull > push * 1.5:
        notes.append(f"拉 {pull:.1f} 组 vs 推 {push:.1f} 组，推类偏少，胸肩发展会受限")
    if legs == 0:
        notes.append("腿部零训练，建议每周至少 6-8 组深蹲/硬拉类")
    elif legs < (push + pull) * 0.4:
        notes.append("腿部容量相对上肢偏低")
    return "；".join(notes) if notes else "推拉腿比例合理"


def volume_trend(workouts: list[dict], weeks: int = 8) -> list[dict]:
    """按周统计总容量与组数。"""
    buckets: dict[str, dict] = {}
    for w in workouts:
        wd = w["date"]
        if isinstance(wd, str):
            wd = date.fromisoformat(wd)
        y, wk, _ = wd.isocalendar()
        key = f"{y}-W{wk:02d}"
        b = buckets.setdefault(key, {"week": key, "sets": 0, "volume": 0.0, "sessions": set()})
        b["sessions"].add(str(wd))
        for s in w["sets"]:
            if s.get("is_warmup"):
                continue
            b["sets"] += 1
            b["volume"] += (s.get("weight_kg") or 0) * (s.get("reps") or 0)
    out = [
        {"week": b["week"], "sets": b["sets"], "volume_kg": round(b["volume"]), "sessions": len(b["sessions"])}
        for b in sorted(buckets.values(), key=lambda x: x["week"])
    ]
    return out[-weeks:]


def personal_records(workouts: list[dict]) -> list[dict]:
    """每个动作的最佳 e1RM（Epley）。"""
    best: dict[str, dict] = {}
    for w in workouts:
        for s in w["sets"]:
            wt, reps = s.get("weight_kg") or 0, s.get("reps") or 0
            if wt <= 0 or reps <= 0 or reps > 20:
                continue
            e1rm = wt * (1 + reps / 30.0)
            name = s.get("exercise_name") or s.get("exercise_id")
            if name not in best or e1rm > best[name]["e1rm"]:
                best[name] = {
                    "exercise": name,
                    "e1rm": round(e1rm, 1),
                    "weight_kg": wt,
                    "reps": reps,
                    "date": str(w["date"]),
                }
    return sorted(best.values(), key=lambda x: -x["e1rm"])


def suggest_plan(
    goal: str,
    days_per_week: int,
    weak_muscles: list[str] | None = None,
    focus: list[str] | None = None,
) -> dict:
    """基于目标与频率生成周计划模板。"""
    weak_muscles = weak_muscles or []
    focus = focus or []

    if days_per_week <= 3:
        template = [
            ("全身 A", ["杠铃深蹲", "杠铃卧推", "杠铃划船", "侧平举", "平板支撑"]),
            ("全身 B", ["硬拉", "哑铃肩推", "高位下拉", "腿弯举", "卷腹"]),
            ("全身 C", ["腿举", "上斜哑铃卧推", "坐姿绳索划船", "面拉", "站姿提踵"]),
        ][:days_per_week]
    elif days_per_week == 4:
        template = [
            ("上肢 A（推主导）", ["杠铃卧推", "哑铃肩推", "高位下拉", "侧平举", "绳索下压"]),
            ("下肢 A（股四主导）", ["杠铃深蹲", "腿举", "腿弯举", "站姿提踵", "平板支撑"]),
            ("上肢 B（拉主导）", ["引体向上", "坐姿绳索划船", "反向飞鸟", "杠铃弯举", "面拉"]),
            ("下肢 B（后链主导）", ["硬拉", "臀桥", "保加利亚分腿蹲", "悬垂举腿"]),
        ]
    else:
        template = [
            ("推", ["杠铃卧推", "上斜哑铃卧推", "哑铃肩推", "侧平举", "绳索下压"]),
            ("拉", ["引体向上", "杠铃划船", "坐姿绳索划船", "面拉", "杠铃弯举"]),
            ("腿", ["杠铃深蹲", "腿举", "腿弯举", "站姿提踵", "卷腹"]),
            ("上肢补充", ["哑铃卧推", "高位下拉", "反向飞鸟", "锤式弯举", "过顶臂屈伸"]),
            ("下肢补充", ["硬拉", "臀桥", "箭步蹲", "髋外展", "悬垂举腿"]),
        ][:days_per_week]

    plan_days = []
    for i, (name, exs) in enumerate(template):
        plan_days.append(
            {
                "day_index": i,
                "name": name,
                "exercises": [
                    {"exercise": e, "sets": 3 if i else 4, "reps": "6-10", "rest_s": 120, "note": ""}
                    for e in exs
                ],
            }
        )

    if weak_muscles:
        for d in plan_days:
            d["note"] = f"本周补强：{', '.join(MUSCLE_CN.get(m, m) for m in weak_muscles[:3])}"

    return {
        "goal": goal,
        "days_per_week": days_per_week,
        "split": "全身" if days_per_week <= 3 else ("上下肢" if days_per_week == 4 else "推拉腿"),
        "days": plan_days,
        "progression": "每周在动作能完成上限次数时加 2.5kg（上肢）/ 5kg（下肢），或加 1 组",
        "focus": focus,
    }