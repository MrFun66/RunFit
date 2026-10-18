import io
js=io.open("web/assets/app.js",encoding="utf-8").read()
i=js.find("currentMealResult")
print("idx",i)
print(js[i-200:i+3200])
