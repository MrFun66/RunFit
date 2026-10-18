import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('id="modal-meal"')
print("idx",i)
print(h[i-300:i+2600])
