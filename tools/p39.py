import io,re
js=io.open("web/assets/app.js",encoding="utf-8").read()
for kw in ["btn-save-meal","meal-slot-pick","currentMealResult"]:
    print("===",kw,"count",js.count(kw))
    for m in re.finditer(re.escape(kw), js):
        print("   @",m.start(),"|",js[max(0,m.start()-100):m.start()+140].replace("\n"," "))
