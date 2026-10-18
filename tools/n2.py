import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
i=s.find("def _ingest_csv")
print("_ingest_csv idx",i)
if i>0: print(s[i-1200:i+200])
else:
    j=s.find("helper inserted")
    print("no _ingest_csv; searching for csv")
    import re
    for m in re.finditer(r'def _\w*csv\w*', s):
        print(" ", m.group(0), m.start())
