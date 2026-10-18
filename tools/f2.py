import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
i=s.find('@router.get("/config")')
print("config idx",i)
print(s[i-700:i+300])
