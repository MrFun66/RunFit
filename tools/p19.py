import io
a=io.open("app/api.py",encoding="utf-8").read()
i=a.find('@router.get("/foods")')
print("=== first /foods block idx",i,"===")
print(a[i-500:i+2500])
