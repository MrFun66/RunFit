import io
a=io.open("app/api.py",encoding="utf-8").read()
i=a.find('@router.get("/nutrition/plan")')
print("=== nutrition/plan ===")
print(a[i:i+2600])
