import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
i=s.find('    try:\n        body = await request.json()')
print("idx",i)
print(s[i-700:i+1500])
