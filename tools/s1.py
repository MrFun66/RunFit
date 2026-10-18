import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
i=s.find('@router.post("/health")')
print("idx",i)
print(s[i:i+2600])
