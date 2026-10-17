import io, re

# ---------- backend ----------
p = "app/api.py"
s = io.open(p, encoding="utf-8").read()
a = s.find('@router.get("/strength/trend")')
b = s.find('@router.put("/workouts/{wid:int}")')
assert a > 0 and b > a, (a, b)

new_backend = '''@router.get("/strength/trend")
def strength_trend(
    grain: str = Query("day", pattern="^(day|week|month|year)$"),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """按肌群分色堆叠的力量训练容量柱状图。

    day   最近 7 天，每根柱子按肌群堆叠
    week  本周 7 天（周一 ... 周日）
    month 本月各周（第一周 ... 第五周）
    year  今年 12 个月（1月 ... 12月）
    """
    from collections import defaultdict

    today = date.today()
    buckets: list = []

    if grain == "day":
        for k in range(6, -1, -1):
            d = today - timedelta(days=k)
            buckets.append((d.isoformat(), "%d/%d" % (d.month, d.day)))
        start, end = today - timedelta(days=6), today
    elif grain == "week":
        monday = today - timedelta(days=today.weekday())
        names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for k in range(7):
            d = monday + timedelta(days=k)
            buckets.append((d.isoformat(), names[k]))
        start, end = monday, monday + timedelta(days=6)
    elif grain == "month":
        first = today.replace(day=1)
        last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        n = 0
        d = first
        while d <= last:
            n += 1
            buckets.append(("%d-%02d-W%d" % (first.year, first.month, n), "第%d周" % n))
            d += timedelta(days=7)
        start, end = first, last
    else:
        for m in range(1, 13):
            buckets.append(("%d-%02d" % (today.year, m), "%d月" % m))
        start, end = date(today.year, 1, 1), date(today.year, 12, 31)

    workouts = db.scalars(
        select(Workout)
        .where(Workout.user_id == user.id, Workout.date >= start, Workout.date <= end)
        .order_by(Workout.date)
    ).all()

    ex_map = {ex.id: ex for ex in db.scalars(select(Exercise)).all()}

    idx_of = {k: i for i, (k, _) in enumerate(buckets)}
    data = {p: [0.0] * len(buckets) for p, _, _ in PART_META}
    set_count = {p: 0 for p, _, _ in PART_META}
    top_ex = defaultdict(lambda: defaultdict(float))

    for w in workouts:
        d = w.date
        if grain in ("day", "week"):
            key = d.isoformat()
        elif grain == "month":
            key = "%d-%02d-W%d" % (d.year, d.month, (d.day - 1) // 7 + 1)
        else:
            key = "%d-%02d" % (d.year, d.month)
        pos = idx_of.get(key)
        if pos is None:
            continue
        for st in w.sets:
            if st.is_warmup:
                continue
            vol = float((st.weight_kg or 0) * (st.reps or 0))
            if vol <= 0:
                vol = float(st.reps or 0)
            if vol <= 0:
                continue
            ex = ex_map.get(st.exercise_id)
            parts = _muscles_to_parts(getattr(ex, "primary_muscles", None)) if ex else []
            if not parts and ex is not None:
                cat = (getattr(ex, "category", "") or "").lower()
                parts = {"push": ["chest"], "pull": ["back"], "legs": ["legs"], "core": ["core"]}.get(cat, ["core"])
            if not parts:
                parts = ["core"]
            share = vol / len(parts)
            for p in parts:
                data[p][pos] += share
                set_count[p] += 1
                if ex is not None:
                    top_ex[p][ex.name] += share

    series = []
    for p, label, color in PART_META:
        tot = round(sum(data[p]))
        if tot <= 0:
            continue
        tops = sorted(top_ex[p].items(), key=lambda kv: -kv[1])[:3]
        series.append(
            {
                "part": p,
                "label": label,
                "color": color,
                "data": [round(v) for v in data[p]],
                "total": tot,
                "sets": set_count[p],
                "top_exercises": [{"name": nm, "volume": round(v)} for nm, v in tops],
            }
        )

    active = sum(1 for i in range(len(buckets)) if any(data[p][i] > 0 for p, _, _ in PART_META))
    return {
        "grain": grain,
        "buckets": [{"key": k, "label": l} for k, l in buckets],
        "series": series,
        "total_volume": round(sum(x["total"] for x in series)),
        "active_buckets": active,
    }


'''
s = s[:a] + new_backend + s[b:]
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
import ast; ast.parse(s)
print("api.py OK", len(s))
