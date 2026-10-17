import io,re,datetime
ts=datetime.datetime.now().strftime("%Y%m%d%H%M%S")
h=io.open("web/index.html",encoding="utf-8").read()
h2=re.sub(r'app\.js\?v=\d+', 'app.js?v='+ts, h)
io.open("web/index.html","w",encoding="utf-8",newline="\n").write(h2)
sw=io.open("web/sw.js",encoding="utf-8").read()
sw2=re.sub(r"grf-\d+", "grf-"+ts, sw)
io.open("web/sw.js","w",encoding="utf-8",newline="\n").write(sw2)
print("bumped", ts, h!=h2, sw!=sw2)
