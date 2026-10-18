import io,re
h=io.open("web/index.html",encoding="utf-8").read()
for m in re.finditer(r'id="modal-food"', h):
    print("modal-food @", m.start())
i=h.find('id="modal-food"')
if i>0:
    print(h[i-100:i+2400])
