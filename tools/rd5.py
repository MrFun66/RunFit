import io,re
h=io.open("web/index.html",encoding="utf-8").read()
print("trend-legend:", 'id="trend-legend"' in h)
m=re.search(r'app\.js\?v=(\d+)', h); print("v:", m.group(1))
i=h.find('id="trend-grain"')
print(h[max(0,i-100):i+1100])
