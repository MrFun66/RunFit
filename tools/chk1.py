import io
a=io.open("app/api.py",encoding="utf-8").read()
print("has /foods route:", '"/foods"' in a)
print("foods. used:", a.count("foods."))
i=a.find("from . import analytics, foods")
print(a[i:i+200])
