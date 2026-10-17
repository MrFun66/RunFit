import io
s=io.open("web/assets/app.js",encoding="utf-8").read()
i=s.find("async function loadStrengthTrend")
j=s.find("// \u7f16\u8f91\u5f53\u5929\u8bb0\u5f55")
if j<0:
    j=s.find("function editWorkout", i)
print("i",i,"j",j)
print(s[i:j])
