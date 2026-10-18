import io
js=io.open("web/assets/app.js",encoding="utf-8").read()
for kw in ["meals_complete","slots_done","target","/foods"]:
    print(kw, "->", js.count(kw))
