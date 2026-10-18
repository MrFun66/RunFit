import io
n=io.open("app/nutrition.py",encoding="utf-8").read()
print("len",len(n))
print(n[:3000])
