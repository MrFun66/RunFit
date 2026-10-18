import io,re
s=io.open("app/sync_api.py",encoding="utf-8").read()
print("=== endpoint 生成相关 ===")
for m in re.finditer(r'endpoint', s):
    seg = s[max(0,m.start()-200):m.start()+200]
    print("@", m.start(), "|", seg.replace("\n"," ")[:380])
    print("---")
