import io
p="web/assets/app.js"
s=io.open(p,encoding="utf-8").read()
print("js len",len(s))
i=s.find('var locked = document.getElementById("macro-locked");')
j=s.find('// ---------- 2. 餐食列表 ----------')
print("locked @",i,"list @",j)
print(repr(s[i:i+120]))
print(repr(s[j-260:j+60]))
