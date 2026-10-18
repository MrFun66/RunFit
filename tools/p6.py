import io,re
js=io.open("web/assets/app.js",encoding="utf-8").read()
html=io.open("web/index.html",encoding="utf-8").read()
sw=io.open("web/sw.js",encoding="utf-8").read()
print("js len",len(js))
print("installShortcut occurrences:", js.count("installShortcut"))
for m in re.finditer(r"installShortcut", js):
    print("  ctx:", js[max(0,m.start()-80):m.start()+60].replace("\n"," "))
print("--- index app.js ver ---")
for m in re.finditer(r'app\.js\?v=([0-9]+)', html):
    print("  ", m.group(1))
print("--- sw cache ---")
for m in re.finditer(r"grf-[0-9]+", sw):
    print("  ", m.group(0))
