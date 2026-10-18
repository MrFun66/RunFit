import io
p = r"D:\GRF\app\sync_api.py"
s = io.open(p, encoding="utf-8").read()

start = s.index("def _ingest_csv_text(")
end = s.index("_SAMPLE_CACHE: dict = {}")
print("block len:", end - start)

new = '''def _ingest_csv_text(db: OrmSession, user: User, text: str) -> dict:
    """解析 HAE 导出的 CSV（宽表或长表），返回统计。

    性能要点：整份 CSV 先在内存里聚合（同一天同一指标只保留最后一条），
    再做一次批量 select + 批量 insert，避免逐行查库导致大文件超时。
    """
    import csv as _csv
    import io as _io

    text = text.lstrip("\\ufeff")
    if not text.strip():
        return {"metrics": 0, "runs": 0}

    sample = text[:4096]
    delim = ","
    for cand in (",", ";", "\\t"):
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


'''

s = s[:start] + new + s[end:]

# 定义 _BODY_FIELDS（放在 _csv_store 之前）
if "_BODY_FIELDS = (" not in s:
    s = s.replace(
        "_SAMPLE_CACHE: dict = {}",
        '_BODY_FIELDS = ("weight_kg", "bodyfat_pct", "resting_hr", "sleep_hours",\n'
        '                "muscle_kg", "waist_cm", "hip_cm", "chest_cm", "arm_cm", "thigh_cm")\n\n'
        "_SAMPLE_CACHE: dict = {}",
        1,
    )

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("new len", len(s))
import ast
ast.parse(s)
print("AST_OK")
