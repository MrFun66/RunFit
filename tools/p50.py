import io
f=io.open("app/foods.py",encoding="utf-8").read()
print("foods.py len",len(f),"| has search:", "def search" in f, "| has compute:", "def compute" in f, "| FOODS count:", f.count('"name":'))
