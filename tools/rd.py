import io
s=io.open("web/assets/app.js",encoding="utf-8").read()
i=s.find("async function loadStrengthTrend")
j=s.find("// 编辑当天记录（整体替换）")
if j<0: j=s.find("function editWorkout")
print("i",i,"j",j)
print(s[i:j])
print("=== import json in api.py:", "import json" in io.open("app/api.py",encoding="utf-8").read())
