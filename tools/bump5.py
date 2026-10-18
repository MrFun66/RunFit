import io,re,datetime
stamp=datetime.datetime.now().strftime("%Y%m%d%H%M%S")
h=io.open("web/index.html",encoding="utf-8").read()
h=re.sub(r'app\.js\?v=\d+', 'app.js?v='+stamp, h)
io.open("web/index.html","w",encoding="utf-8",newline="\n").write(h)
s=io.open("web/sw.js",encoding="utf-8").read()
s=re.sub(r'grf-\d+', 'grf-'+stamp, s)
io.open("web/sw.js","w",encoding="utf-8",newline="\n").write(s)
print("ver",stamp,"len",len(h))
