import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
i=s.find('@router.post("/health")')
k=s.find('return {', i)
print(s[k-600:k+500])
