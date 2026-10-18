import io,re
h=io.open("web/index.html",encoding="utf-8").read()
print("html len",len(h))
for m in re.finditer(r'id="tab-(nutrition|diet|food)[^"]*"', h):
    print("TAB:",m.group(0), m.start())
i=h.find('id="tab-nutrition"')
if i<0: i=h.find('id="tab-diet"')
print("=== nutrition tab block idx",i,"===")
print(h[i:i+3000])
