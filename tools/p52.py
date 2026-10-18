import io
a=io.open("app/api.py",encoding="utf-8").read()
i=a.find('@router.post("/meals/photo")')
print("photo idx",i)
print(a[i-2600:i+200])
