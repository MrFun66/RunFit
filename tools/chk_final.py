import io,re
s=io.open("web/assets/app.js",encoding="utf-8").read()
for name in ["function renderStrengthChart","function loadStrengthTrend","function editWorkout","function saveWorkoutEdit"]:
    print(name, len(re.findall(re.escape(name), s)))
i=s.find("function loadTodayWorkouts")
print("--- workout card ---")
print(s[i:i+1500])
