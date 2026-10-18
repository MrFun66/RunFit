import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('id="modal-food"')
j=h.find('id="modal-meal"')
print(h[i-200:j])
