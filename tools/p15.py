import io
js=io.open("web/assets/app.js",encoding="utf-8").read()
i=js.find("async function loadNutrition")
if i<0:
    i=js.find("function loadNutrition")
print("idx",i)
print(js[i:i+5200])
