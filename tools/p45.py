import io
p="app/api.py"
a=io.open(p,encoding="utf-8").read()
old = '''    return {"complete": True, "tdee": t, "weekly_km": round(weekly_km, 1), "plan": weekly}'''
new = '''    per = weekly.get("per_day_type") or {}
    return {
        "complete": True,
        "tdee": t,
        "weekly_km": round(weekly_km, 1),
        # 兼容旧前端：把 per_day_type 摊平到顶层
        "plan": {**weekly, **per},
    }'''
assert old in a, "plan return not found"
a = a.replace(old, new, 1)
io.open(p,"w",encoding="utf-8",newline="\n").write(a)
print("patched2", len(a))
