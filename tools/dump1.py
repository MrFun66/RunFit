import io, re
s = io.open("web/assets/app.js", encoding="utf-8").read()
out = []
out.append("LEN=%d" % len(s))
out.append("--- function signatures ---")
for m in re.finditer(r"^(async\s+)?function\s+(\w+)", s, re.M):
    out.append(("async " if m.group(1) else "       ") + m.group(2))
out.append("--- editWorkout region ---")
i = s.find("function editWorkout")
out.append(s[i-30:i+1200])
out.append("--- saveWorkoutEdit region ---")
j = s.find("function saveWorkoutEdit")
out.append(s[j-30:j+1500])
io.open("tools/dump.txt","w",encoding="utf-8").write("\n".join(out))
print("ok")
