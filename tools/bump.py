import io, re, datetime
v = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

# 1) index.html 版本号
p = r"D:\GRF\web\index.html"
s = io.open(p, encoding="utf-8").read()
s2 = re.sub(r"app\.js\?v=\d+", "app.js?v=" + v, s)
io.open(p, "w", encoding="utf-8", newline="\n").write(s2)
print("html ver", v, len(s), "->", len(s2))

# 2) sw.js 缓存名
q = r"D:\GRF\web\sw.js"
t = io.open(q, encoding="utf-8").read()
t2 = re.sub(r"grf-[\w\-\.]+", "grf-" + v, t)
io.open(q, "w", encoding="utf-8", newline="\n").write(t2)
print("sw ver", v)
