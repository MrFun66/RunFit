import io
p="app/api.py"
s=io.open(p,encoding="utf-8").read()
i=s.index('@router.get("/strength/trend")')
j=s.index('@router.put("/workouts/{wid:int}")')
new = r'''@router.get("/strength/trend")
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


'''
s = s[:i] + new + s[j:]
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
import ast; ast.parse(s); print("api.py OK len", len(s))
