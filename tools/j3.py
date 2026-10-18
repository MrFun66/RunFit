import io
p="web/assets/app.js"
s=io.open(p,encoding="utf-8").read()
i=s.find('function _renderFoodList(items)')
j=s.find('function _renderBasket()')
print("renderFoodList @",i,"renderBasket @",j)
print(s[i:j])
