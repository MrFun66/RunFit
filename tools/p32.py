import io,re
js=io.open("web/assets/app.js",encoding="utf-8").read()
for kw in ["modal-food","food-search","food-list","btn-open-food"]:
    print("=== ",kw," ===")
    for m in re.finditer(re.escape(kw), js):
        print("  @",m.start(),"|", js[max(0,m.start()-160):m.start()+160].replace("\n"," "))
