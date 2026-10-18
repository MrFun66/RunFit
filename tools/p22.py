import io,re
a=io.open("app/api.py",encoding="utf-8").read()
i=a.find("def list_meals")
print("list_meals idx",i)
print(a[i-200:i+3000])
