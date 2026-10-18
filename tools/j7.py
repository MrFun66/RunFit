import io
p="web/assets/app.js"
s=io.open(p,encoding="utf-8").read()
orig=len(s)

# 1) 声明 _foodListCache（放在 _foodBasket 声明旁）
old_decl = 'var _foodBasket = [];'
assert old_decl in s
if '_foodListCache' not in s.split('function _renderFoodList')[0]:
    s = s.replace(old_decl, 'var _foodBasket = [];\nvar _foodListCache = [];', 1)
    print("[1] declared _foodListCache")

# 2) _addToBasket 支持指定克重
old = '''function _addToBasket(food) {
    var exist = null;
    for (var i = 0; i < _foodBasket.length; i++) {
        if (_foodBasket[i].name === food.name) { exist = _foodBasket[i]; break; }
    }
    if (exist) {
        exist.grams += food.unit_g;
    } else {
        _foodBasket.push({ name: food.name, grams: food.unit_g, unit_g: food.unit_g, kcal: food.kcal, p: food.p, c: food.c, f: food.f });
    }
    _renderBasket();
}'''
new = '''function _addToBasket(food, grams) {
    var g = (grams === undefined || grams === null) ? food.unit_g : Math.max(1, Math.round(grams));
    var exist = null;
    for (var i = 0; i < _foodBasket.length; i++) {
        if (_foodBasket[i].name === food.name) { exist = _foodBasket[i]; break; }
    }
    if (exist) {
        exist.grams = Math.round(exist.grams + g);
    } else {
        _foodBasket.push({ name: food.name, grams: g, unit_g: food.unit_g, kcal: food.kcal, p: food.p, c: food.c, f: food.f });
    }
    _renderBasket();
}'''
assert old in s, "addToBasket not matched"
s = s.replace(old, new, 1)
print("[2] _addToBasket grams param")

# 3) 初始化份量面板
old_init = 'document.addEventListener("DOMContentLoaded", initFoodModal);'
assert old_init in s
s = s.replace(old_init, 'document.addEventListener("DOMContentLoaded", function () { initFoodModal(); initPortionPanel(); });', 1)
old_init2 = 'if (document.readyState !== "loading") initFoodModal();'
assert old_init2 in s
s = s.replace(old_init2, 'if (document.readyState !== "loading") { initFoodModal(); initPortionPanel(); }', 1)
print("[3] initPortionPanel hooked")

io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("len", orig, "->", len(s))
