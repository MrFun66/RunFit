import io
p="web/assets/app.js"
s=io.open(p,encoding="utf-8").read()
orig=len(s)

i=s.find('var locked = document.getElementById("macro-locked");')
j=s.find('// ---------- 2. \u9910\u98df\u5217\u8868 ----------')
assert i>0 and j>i, (i,j)

new_block = '''var locked = document.getElementById("macro-locked");
    var body = document.getElementById("macro-body");
    var badge = document.getElementById("mac-badge");
    var hasAny = !!(data && data.items && data.items.length);
    var tgt = (data && data.target) || null;
    var tot = (data && data.total) || { kcal: 0, protein_g: 0, carb_g: 0, fat_g: 0 };

    // 只要记录过任意一餐就解锁显示（不要求三餐齐全）
    if (hasAny && tgt) {
        if (locked) locked.classList.add("hidden");
        if (body) body.classList.remove("hidden");
        var slotsDone = (data && data.slots_done) || [];
        var MEAL_N = { breakfast: "\\u65e9", lunch: "\\u5348", dinner: "\\u665a", snack: "\\u52a0" };
        if (badge) {
            badge.textContent = "\\u5df2\\u8bb0 " + slotsDone.length + " \\u9910";
            badge.className = "text-[10px] bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full";
        }
        _setTxt("mac-kcal", Math.round(tot.kcal || 0));
        _setTxt("mac-kcal-t", Math.round(tgt.kcal || 0));
        _setTxt("mac-p", Math.round(tot.protein_g || 0));
        _setTxt("mac-p-t", Math.round(tgt.protein_g || 0));
        _setTxt("mac-c", Math.round(tot.carb_g || 0));
        _setTxt("mac-c-t", Math.round(tgt.carb_g || 0));
        _setTxt("mac-f", Math.round(tot.fat_g || 0));
        _setTxt("mac-f-t", Math.round(tgt.fat_g || 0));
        _setTxt("mac-daytype", DAYTYPE_LABEL[tgt.day_type] || "\\u8bad\\u7ec3\\u65e5");
    } else {
        if (locked) locked.classList.remove("hidden");
        if (body) body.classList.add("hidden");
        if (badge) {
            badge.textContent = hasAny ? "\\u5f85\\u8865\\u8eab\\u4f53\\u6570\\u636e" : "\\u672a\\u8bb0\\u5f55";
            badge.className = "text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full";
        }
    }

    '''
s = s[:i] + new_block + s[j:]
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("block replaced:", orig, "->", len(s))
