import io,re
h=io.open("web/index.html",encoding="utf-8").read()
sw=io.open("web/sw.js",encoding="utf-8").read()
print("app.js ver:", re.findall(r'app\.js\?v=(\d+)', h))
print("sw cache:", re.findall(r'grf-\d+', sw))
print("modal-foods removed:", '<div id="modal-foods"' not in h)
print("modal-food present:", '<div id="modal-food"' in h)
