import io
n=io.open("app/nutrition.py",encoding="utf-8").read()
i=n.find("def weekly_nutrition")
print(n[i:i+1500])
