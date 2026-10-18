import io
a=io.open("app/api.py",encoding="utf-8").read()
i=a.find('@router.post("/foods/calc")')
print("post /foods/calc @",i)
print(a[i-1400:i+700])
