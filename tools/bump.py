import io, re, datetime
ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

# 1) bump app.js?v= in index.html
p = "web/index.html"
h = io.open(p, encoding="utf-8").read()
h2 = re.sub(r"app\.js\?v=\d+", "app.js?v=" + ts, h)
io.open(p, "w", encoding="utf-8", newline="\n").write(h2)
print("index.html bumped ->", ts, "changed:", h != h2)

# 2) bump sw.js CACHE_NAME
p2 = "web/sw.js"
sw = io.open(p2, encoding="utf-8").read()
sw2 = re.sub(r"CACHE_NAME\s*=\s*['\"][^'\"]+['\"]", "CACHE_NAME = 'grf-" + ts + "'", sw)
io.open(p2, "w", encoding="utf-8", newline="\n").write(sw2)
print("sw.js bumped ->", "changed:", sw != sw2)

# verify
h3 = io.open(p, encoding="utf-8").read()
print("verify v:", re.search(r"app\.js\?v=(\d+)", h3).group(1))
sw3 = io.open(p2, encoding="utf-8").read()
print("verify cache:", re.search(r"CACHE_NAME\s*=\s*['\"]([^'\"]+)", sw3).group(1))
