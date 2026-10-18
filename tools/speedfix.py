import io, re
p = r"D:\GRF\app\sync_api.py"
s = io.open(p, encoding="utf-8").read()
orig = len(s)

# ---------- 1) _csv_store 不再逐行 commit，改为纯写入 ----------
old_store = '''def _csv_store(db: OrmSession, user: User, day, name: str, val: float, unit) -> None:
    """把一个 CSV 单元格写进 body_metrics 或 health_samples。"""
    field = _METRIC_MAP.get(name.lower())
    if field in ("weight_kg", "bodyfat_pct", "resting_hr", "sleep_hours",
                 "muscle_kg", "waist_cm", "hip_cm", "chest_cm", "arm_cm", "thigh_cm"):
        v = val * 100 if (field == "bodyfat_pct" and val <= 1.5) else val
        _upsert_body(db, user, day, {field: round(v, 2)})
        db.commit()
    else:
        _save_sample(db, user, day, name, val, unit)
        db.commit()'''

new_store = '''_SAMPLE_CACHE: dict = {}


def _csv_store(db: OrmSession, user: User, day, name: str, val: float, unit) -> None:
    """把一个 CSV 单元格写进 body_metrics 或 health_samples。

    注意：这里绝不 commit。逐行 commit 会让 3 万行 CSV 耗时 40 秒以上，
    导致 iPhone 快捷指令超时并报「网络连接已中断」。统一由调用方提交一次。
    """
    field = _METRIC_MAP.get(name.lower())
    if field in ("weight_kg", "bodyfat_pct", "resting_hr", "sleep_hours",
                 "muscle_kg", "waist_cm", "hip_cm", "chest_cm", "arm_cm", "thigh_cm"):
        v = val * 100 if (field == "bodyfat_pct" and val <= 1.5) else val
        _upsert_body(db, user, day, {field: round(v, 2)})
        return

    key = (day, name)
    row = _SAMPLE_CACHE.get(key)
    if row is None:
        row = db.scalars(
            select(HealthSample).where(
                HealthSample.user_id == user.id,
                HealthSample.date == day,
                HealthSample.metric == name,
            )
        ).first()
        _SAMPLE_CACHE[key] = row if row is not None else False
    if row is False or row is None:
        row = HealthSample(
            user_id=user.id, date=day, metric=name,
            value=val, unit=unit, source="auto-sync",
        )
        db.add(row)
        _SAMPLE_CACHE[key] = row
    else:
        row.value = val
        if unit:
            row.unit = unit'''

assert old_store in s, "csv_store anchor not found"
s = s.replace(old_store, new_store, 1)

# ---------- 2) _ingest_csv_text 结尾统一 commit ----------
old_ret = '''            _csv_store(db, user, dt.date(), h, val, None)
            saved += 1
    return {"metrics": saved, "runs": 0}'''
new_ret = '''            _csv_store(db, user, dt.date(), h, val, None)
            saved += 1
    db.commit()
    _SAMPLE_CACHE.clear()
    return {"metrics": saved, "runs": 0}'''
assert old_ret in s, "wide-table return anchor not found"
s = s.replace(old_ret, new_ret, 1)

old_ret2 = '''            _csv_store(db, user, dt.date(), name, val, unit)
            saved += 1
        return {"metrics": saved, "runs": 0}'''
new_ret2 = '''            _csv_store(db, user, dt.date(), name, val, unit)
            saved += 1
        db.commit()
        _SAMPLE_CACHE.clear()
        return {"metrics": saved, "runs": 0}'''
assert old_ret2 in s, "long-table return anchor not found"
s = s.replace(old_ret2, new_ret2, 1)

# 空输入分支也要清理缓存
s = s.replace('''    text = text.lstrip("\\ufeff")
    if not text.strip():
        return {"metrics": 0, "runs": 0}''',
'''    text = text.lstrip("\\ufeff")
    _SAMPLE_CACHE.clear()
    if not text.strip():
        return {"metrics": 0, "runs": 0}''', 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched", orig, "->", len(s))

import ast
ast.parse(s)
print("AST_OK")
