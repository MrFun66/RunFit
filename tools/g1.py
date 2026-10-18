import io,re
s=io.open("app/sync_api.py",encoding="utf-8").read()
print(s[:1200])
print("--- settings usages ---")
for m in re.finditer(r'\bsettings\.', s):
    print(" ", s[max(0,m.start()-40):m.start()+40].replace("\n"," "))
