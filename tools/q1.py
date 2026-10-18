import io
s=io.open("app/sync_api.py",encoding="utf-8").read()
i=s.find('@router.post("/health")')
j=s.find('    body_added = body_updated = 0', i)
print("handler @",i,"| body_added @",j)
print(repr(s[i:j]))
