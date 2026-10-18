import io
a=io.open("app/api.py",encoding="utf-8").read()
i=a.find('def list_meals')
print(a[i-300:i+2600])
