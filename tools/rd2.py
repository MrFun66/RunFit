import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('id="trend-grain"')
print(h[max(0,i-700):i+900])
