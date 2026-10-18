import io
js=io.open("web/assets/app.js",encoding="utf-8").read()
print("js len",len(js))
for kw in ["mac-daytype","mac-kcal-eat","mac-p-eat","mac-kcal-tgt","meal-foods-btn","modal-food","meals_complete"]:
    print(kw, js.count(kw))
