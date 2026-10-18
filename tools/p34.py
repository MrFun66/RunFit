import io,re
js=io.open("web/assets/app.js",encoding="utf-8").read()
i=js.find("function initModals")
print("initModals @",i)
print(js[i:i+2200])
print()
print("=== btn-save-meal binding ===")
for m in re.finditer(r"btn-save-meal", js):
    print("  @",m.start(),"|",js[max(0,m.start()-200):m.start()+200].replace("\n"," "))
