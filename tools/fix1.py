import io
p="app/api.py"
s=io.open(p,encoding="utf-8").read()
old='''            tp = plan["plan"]
            key = "training" if day_type == "training" else ("long_run" if day_type == "long_run" else "rest")
            target = tp.get(key) or tp.get("training")'''
new='''            tp = plan["plan"]
            # nutrition_plan 返回 {"per_day_type": {training/rest/long_run: {...}}, ...}
            if isinstance(tp, dict) and "per_day_type" in tp:
                tp = tp["per_day_type"]
            key = "training" if day_type == "training" else ("long_run" if day_type == "long_run" else "rest")
            target = tp.get(key) or tp.get("training")'''
assert old in s, "anchor not found"
s=s.replace(old,new,1)
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("patched", len(s))
