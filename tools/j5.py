import io
p="web/assets/app.js"
s=io.open(p,encoding="utf-8").read()
orig=len(s)

i=s.find('function _renderFoodList(items) {')
j=s.find('function _addToBasket(food) {')
assert i>0 and j>i

new = '''function _renderFoodList(items) {
    var box = document.getElementById("food-list");
    if (!box) return;
    _foodListCache = items || [];
    if (!items || !items.length) {
        box.innerHTML = '<div class="text-center text-slate-400 text-sm py-6">\\u6ca1\\u627e\\u5230\\uff0c\\u6362\\u4e2a\\u5173\\u952e\\u8bcd\\u8bd5\\u8bd5</div>';
        return;
    }
    var html = "";
    items.forEach(function (f, i) {
        html += '<button data-food-idx="' + i + '" class="w-full text-left px-3 py-2.5 rounded-lg active:bg-slate-100 border-b border-slate-50 last:border-0 flex justify-between items-center">';
        html += '<div class="min-w-0"><div class="text-sm text-slate-700 truncate">' + f.name + "</div>";
        html += '<div class="text-[11px] text-slate-400">\\u6bcf100g ' + f.kcal + " kcal \\u00b7 P" + f.p + " C" + f.c + " F" + f.f + "</div></div>";
        html += '<span class="text-[11px] text-brand font-bold shrink-0 ml-2">\\u4e00\\u4efd ' + f.unit_g + "g \\u203a</span>";
        html += "</button>";
    });
    box.innerHTML = html;
    box.querySelectorAll("[data-food-idx]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var f = items[parseInt(btn.getAttribute("data-food-idx"), 10)];
            if (f) openPortion(f);
        });
    });
}

// ===== \\u4efd\\u91cf\\u9762\\u677f\\uff08\\u5b66 Keep\\uff09 =====
var _portionFood = null;

function openPortion(food) {
    _portionFood = food;
    var list = document.getElementById("food-list");
    var wrap = document.getElementById("food-basket-wrap");
    var pane = document.getElementById("food-portion");
    var srch = document.getElementById("food-search");
    if (list) list.classList.add("hidden");
    if (wrap) wrap.classList.add("hidden");
    if (srch) srch.parentElement.classList.add("hidden");
    if (pane) pane.classList.remove("hidden");

    _setTxt("portion-name", food.name);
    _setTxt("portion-per100", "\\u6bcf100g " + food.kcal + " kcal \\u00b7 P" + food.p + " C" + food.c + " F" + food.f);
    var inp = document.getElementById("portion-grams");
    if (inp) inp.value = food.unit_g;

    // \\u9884\\u8bbe\\u4efd\\u91cf
    var box = document.getElementById("portion-presets");
    if (box) {
        var presets = [food.unit_g, food.unit_g * 2, 100, 150];
        var seen = {};
        var arr = [];
        presets.forEach(function (g) {
            var v = Math.round(g);
            if (v > 0 && !seen[v]) { seen[v] = 1; arr.push(v); }
        });
        box.innerHTML = arr.map(function (g) {
            return '<button data-preset="' + g + '" class="px-3 py-1.5 rounded-full bg-slate-100 text-slate-600 text-xs font-medium">' + g + "g</button>";
        }).join("");
        box.querySelectorAll("[data-preset]").forEach(function (b) {
            b.addEventListener("click", function () {
                if (inp) inp.value = b.getAttribute("data-preset");
                _updatePortionPreview();
            });
        });
    }
    _updatePortionPreview();
}

function closePortion() {
    var list = document.getElementById("food-list");
    var wrap = document.getElementById("food-basket-wrap");
    var pane = document.getElementById("food-portion");
    var srch = document.getElementById("food-search");
    if (pane) pane.classList.add("hidden");
    if (list) list.classList.remove("hidden");
    if (wrap) wrap.classList.remove("hidden");
    if (srch) srch.parentElement.classList.remove("hidden");
    _portionFood = null;
}

function _portionGrams() {
    var inp = document.getElementById("portion-grams");
    var v = inp ? parseFloat(inp.value) : 0;
    if (isNaN(v) || v <= 0) v = 1;
    return Math.min(v, 3000);
}

function _updatePortionPreview() {
    if (!_portionFood) return;
    var g = _portionGrams();
    var k = g / 100;
    _setTxt("pv-kcal", Math.round(_portionFood.kcal * k));
    _setTxt("pv-p", Math.round(_portionFood.p * k));
    _setTxt("pv-c", Math.round(_portionFood.c * k));
    _setTxt("pv-f", Math.round(_portionFood.f * k));
}

function initPortionPanel() {
    var pane = document.getElementById("food-portion");
    if (!pane || pane._bound) return;
    pane._bound = true;

    var inp = document.getElementById("portion-grams");
    if (inp) inp.addEventListener("input", _updatePortionPreview);

    var minus = document.getElementById("portion-minus");
    if (minus) minus.addEventListener("click", function () {
        if (inp) inp.value = Math.max(1, Math.round(_portionGrams() - 10));
        _updatePortionPreview();
    });
    var plus = document.getElementById("portion-plus");
    if (plus) plus.addEventListener("click", function () {
        if (inp) inp.value = Math.round(_portionGrams() + 10);
        _updatePortionPreview();
    });

    var back = document.getElementById("portion-back");
    if (back) back.addEventListener("click", closePortion);

    var add = document.getElementById("portion-add");
    if (add) add.addEventListener("click", function () {
        if (!_portionFood) return;
        var g = _portionGrams();
        _addToBasket({
            name: _portionFood.name, unit_g: g,
            kcal: _portionFood.kcal, p: _portionFood.p, c: _portionFood.c, f: _portionFood.f
        }, g);
        closePortion();
        _toast("\\u5df2\\u52a0\\u5165\\uff1a" + _portionFood.name + " " + Math.round(g) + "g");
    });
}

function _toast(msg) {
    var t = document.createElement("div");
    t.className = "fixed left-1/2 -translate-x-1/2 bottom-24 bg-slate-800 text-white text-xs px-4 py-2 rounded-full z-[60] shadow-lg";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.style.opacity = "0"; t.style.transition = "opacity .3s"; }, 1200);
    setTimeout(function () { t.remove(); }, 1600);
}

'''
s = s[:i] + new + s[j:]
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("food list + portion replaced:", orig, "->", len(s))
