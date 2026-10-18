import io
p="web/assets/app.js"
s=io.open(p,encoding="utf-8").read()
print("_foodListCache:", s.count("_foodListCache"))
i=s.find("function _addToBasket(food)")
print("_addToBasket @",i)
print(s[i:i+700])
print()
print("initFoodModal call:", s.count("initFoodModal"))
i=s.find("document.addEventListener(\"DOMContentLoaded\", initFoodModal)")
print(s[i:i+160])
