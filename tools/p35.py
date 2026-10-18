import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('<div id="modal-foods"')
print(h[i:i+2200])
