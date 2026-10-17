import io
p="app/api.py"
s=io.open(p,encoding="utf-8").read()
i=s.find("@router.get(\"/strength/trend\")")
j=s.find("@router.put(\"/workouts/{wid:int}\")")
assert i>0 and j>i

new = '''MUSCLE_TO_PART = {
    "chest": "chest",
    "lats": "back", "mid_back": "back", "lower_back": "back", "traps": "back",
    "front_delt": "shoulder", "side_delt": "shoulder", "rear_delt": "shoulder",
    "biceps": "arms", "triceps": "arms", "forearm": "arms",
    "quads": "legs", "hamstrings": "legs", "glutes": "legs", "calves": "legs",
    "abs": "core", "obliques": "core", "hip_flexor": "core",
}

PART_META = [
    ("chest", "\\u80f8", "#f97316"),
    ("back", "\\u80cc", "#0ea5e9"),
    ("shoulder", "\\u80a9", "#a855f7"),
    ("arms", "\\u624b\\u81c2", "#22c55e"),
    ("legs", "\\u817f", "#ef4444"),
    ("core", "\\u6838\\u5fc3", "#eab308"),
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
    """\\u529b\\u91cf\\u8bad\\u7ec3\\u5bb9\\u91cf\\u67f1\\u72b6\\u56fe\\uff1a\\u6309\\u65e5/\\u5468/\\u6708/\\u5e74\\u5206\\u6876\\uff0c\\u5e76\\u6309\\u8bad\\u7ec3\\u90e8\\u4f4d\\u5206\\u8272\\u5806\\u53e0\\u3002"""
    from collections import defaultdict

    today = date.today()
    buckets: list = []  # [(key, label)]
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

    ex_map = {}
    for ex in db.scalars(select(Exercise)).all():
        ex_map[ex.id] = ex

    keys = [b[0] for b in buckets]
    idx_of = {k: n for n, k in enumerate(keys)}
    data = {p: [0.0 for _ in buckets] for p, _, _ in PART_META}
    set_count = {p: 0 for p, _, _ in PART_META}
    buckets_used = set()

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
                vol = float(st.reps or 0)  # \\u81ea\\u91cd\\u52a8\\u4f5c\\u9000\\u5316\\u4e3a\\u6b21\\u6570
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
        buckets_used.add(pos)

    series = []
    for p, label, color in PART_META:
        tot = round(sum(data[p]))
        series.append({
            "part": p,
            "label": label,
            "color": color,
            "data": [round(v) for v in data[p]],
            "total": tot,
            "sets": set_count[p],
        })
    series = [x for x in series if x["total"] > 0]

    return {
        "grain": grain,
        "buckets": [{"key": k, "label": l} for k, l in buckets],
        "series": series,
        "total_volume": round(sum(x["total"] for x in series)),
        "active_buckets": len(buckets_used),
    }


'''

s = s[:i] + new + s[j:]
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("api.py written, len", len(s))
