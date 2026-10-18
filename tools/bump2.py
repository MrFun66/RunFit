import io, re, datetime
v = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
p=r"D:\GRF\web\index.html"
s=io.open(p,encoding="utf-8").read()
s=re.sub(r"app\.js\?v=\d+", "app.js?v="+v, s)
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
q=r"D:\GRF\web\sw.js"
t=io.open(q,encoding="utf-8").read()
t=re.sub(r"grf-[\w\-\.]+", "grf-"+v, t)
io.open(q,"w",encoding="utf-8",newline="\n").write(t)
print("ver", v, "| html", len(s))
