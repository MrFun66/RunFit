import io,re
js=io.open("web/assets/app.js",encoding="utf-8").read()
for kw in ["loadNutrition","mac-kcal","meal-list","meal-upload","renderMeals","meal-photo"]:
    print("=== ",kw,"count",js.count(kw)," ===")
    for m in re.finditer(re.escape(kw), js):
        print("   @",m.start(), js[max(0,m.start()-60):m.start()+70].replace("\n"," "))
        break
