import io, re
s = io.open("app/api.py", encoding="utf-8").read()
start = s.index('@router.get("/strength/trend")')
end = s.index('@router.put("/workouts/{wid:int}")')
new = '''@router.get("/strength/trend")
def strength_trend(
    grain: str = Query("day", pattern="^(day|week|month|year)$"),
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    """力量训练容量柱状图：按日/周/月/年分桶，按训练部位分色堆叠。"""
    from collections import defaultdict

    today = date.today()
    buckets: list = []
    if grain == "day":
        names = ["\\u5468\\u4e00", "\\u5468\\u4e8c", "\\u5468\\u4e09", "\\u5468\\u56db", "\\u5468\\u4e94", "\\u5468\\u516d", "\\u5468\\u65e5"]
        for k in range(6, -1, -1):
            d = today - timedelta(days=k)
            buckets.append((d.isoformat(), names[d.weekday()]))
        start = today - timedelta(days=6)
    elif grain == "week":
        monday = today - timedelta(days=today.weekday())
        for k in range(7, -1, -1):
            mon = monday - timedelta(weeks=k)
            yy, ww, _ = mon.isocalendar()
            buckets.append((f"{yy}-W{ww:02d}", f"\\u7b2c{ww}\\u5468"))
        start = monday - timedelta(weeks=7)
    elif grain == "month":
        y0, m0 = today.year, today.month
        for k in range(11, -1, -1):
            y, m = y0, m0 - k
            while m <= 0:
                m += 12
                y -= 1
            buckets.append((f"{y}-{m:02d}", f"{m}\\u6708"))
        sy, sm = buckets[0][0].split("-")
        start = date(int(sy), int(sm), 1)
    else:
        for k in range(4, -1, -1):
            y = today.year - k
            buckets.append((str(y), f"{y}\\u5e74"))
        start = date(today.year - 4, 1, 1)

    workouts = db.scalars(
        select(Workout).where(Workout.user_id == user.id, Workout.date >= start).order_by(Workout.date)
    ).all()

    ex_map = {ex.id: ex for ex in db.scalars(select(Exercise)).all()}

    keys = [b[0] for b in buckets]
    idx_of = {k: n for n, k in enumerate(keys)}
    data = {p: [0.0 for _ in buckets] for p, _, _ in PART_META}
    set_count = {p: 0 for p, _, _ in PART_META}
    exercise_detail = {p: defaultdict(float) for p, _, _ in PART_META}
    used = set()

    for w in workouts:
        d = w.date
        if grain == "day":
            key = d.isoformat()
        elif grain == "week":
            y, wk, _ = d.isocalendar()
            key = f"{y}-W{wk:02d}"
        elif grain == "month":
            key = f"{d.year}-{d.month:02d}"
        else:
            key = str(d.year)
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
            if not parts:
                cat = (getattr(ex, "category", "") or "").lower() if ex else ""
                parts = {"push": ["chest"], "pull": ["back"], "legs": ["legs"], "core": ["core"]}.get(cat, ["core"])
            share = vol / len(parts)
            for p in parts:
                data[p][pos] += share
                set_count[p] += 1
                if ex is not None:
                    exercise_detail[p][ex.name] += share
        used.add(pos)

    series = []
    for p, label, color in PART_META:
        tot = round(sum(data[p]))
        if tot <= 0:
            continue
        top = sorted(exercise_detail[p].items(), key=lambda kv: -kv[1])[:3]
        series.append({
            "part": p,
            "label": label,
            "color": color,
            "data": [round(v) for v in data[p]],
            "total": tot,
            "sets": set_count[p],
            "top_exercises": [{"name": n, "volume": round(v)} for n, v in top],
        })

    return {
        "grain": grain,
        "buckets": [{"key": k, "label": l} for k, l in buckets],
        "series": series,
        "total_volume": round(sum(x["total"] for x in series)),
        "active_buckets": len(used),
    }


'''
s = s[:start] + new + s[end:]
io.open("app/api.py", "w", encoding="utf-8", newline="\n").write(s)
import ast; ast.parse(s)
print("OK len", len(s))
