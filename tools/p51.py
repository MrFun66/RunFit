import io
a=io.open("app/api.py",encoding="utf-8").read()
i=a.find('@router.get("/foods/search")')
print("block idx",i,"len",len(a))
print(a[i-400:i+2600])
