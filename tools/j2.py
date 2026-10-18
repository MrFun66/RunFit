import io
p="web/assets/app.js"
s=io.open(p,encoding="utf-8").read()
i=s.find('var locked = document.getElementById("macro-locked");')
j=s.find('// ---------- 2. 餐食列表 ----------')
assert i>0 and j>i
print("=== OLD BLOCK ===")
print(s[i:j])
