import io
p="app/api.py"
a=io.open(p,encoding="utf-8").read()
old = '''            tp = plan["plan"]
            key = "training" if day_type == "training" else ("long_run" if day_type == "long_run" else "rest")
            target = tp.get(key) or tp.get("training")'''
new = '''            tp = plan["plan"] or {}
            # weekly_nutrition 返回 {"per_day_type": {...}}，兼容扁平结构
            per = tp.get("per_day_type") or tp
            key = "training" if day_type == "training" else ("long_run" if day_type == "long_run" else "rest")
            target = per.get(key) or per.get("training")'''
assert old in a, "pattern not found"
a = a.replace(old, new, 1)
io.open(p,"w",encoding="utf-8",newline="\n").write(a)
print("patched", len(a))
