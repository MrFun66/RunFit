import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('<div id="modal-food"')
print("modal-food @",i)
print(h[i:i+3800])
