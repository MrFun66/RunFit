import io,re
s=io.open("web/assets/app.js",encoding="utf-8").read()
for name in ["renderStrengthChart","loadStrengthTrend","editWorkout","saveWorkoutEdit"]:
    for m in re.finditer(r'(?:async\s+)?function\s+'+name+r'\s*\(', s):
        print(name, m.start())
