import io
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
orig=len(h)

# 1) 锁定文案：改成「任意一餐后」
old_lock = '''<div id="macro-locked" class="text-xs text-slate-400 py-3 text-center leading-relaxed">
                        早 / 午 / 晚 三餐都记录后<br>这里会显示「已摄入 / 建议摄入」
                    </div>'''
new_lock = '''<div id="macro-locked" class="text-xs text-slate-400 py-3 text-center leading-relaxed">
                        记录任意一餐后<br>这里就会显示「已摄入 / 建议摄入」
                    </div>'''
assert old_lock in h, "lock text not found"
h = h.replace(old_lock, new_lock, 1)

# 2) 在 food-list 后插入份量面板，并给篮子加 id
old_list = '''            <div class="px-4 pt-2 flex-1 overflow-y-auto" id="food-list"></div>
            <div class="border-t border-slate-100 p-3 bg-slate-50">'''
new_list = '''            <div class="px-4 pt-2 flex-1 overflow-y-auto" id="food-list"></div>

            <!-- 份量面板：点食物后出现 -->
            <div id="food-portion" class="hidden flex-1 flex flex-col min-h-0">
                <div class="px-4 pt-3 pb-2 border-b border-slate-100">
                    <div class="text-sm font-bold text-slate-700" id="portion-name">--</div>
                    <div class="text-[11px] text-slate-400 mt-0.5" id="portion-per100">--</div>
                </div>
                <div class="px-4 py-4 flex items-center justify-center gap-4">
                    <button id="portion-minus" class="w-12 h-12 rounded-full bg-slate-100 text-slate-600 text-2xl font-bold leading-none active:bg-slate-200">−</button>
                    <div class="text-center">
                        <input id="portion-grams" type="number" inputmode="decimal" min="1" step="10" value="100"
                               class="w-28 text-center text-3xl font-bold text-slate-800 border-0 border-b-2 border-brand focus:outline-none bg-transparent">
                        <div class="text-xs text-slate-400 mt-1">克 (g)</div>
                    </div>
                    <button id="portion-plus" class="w-12 h-12 rounded-full bg-brand text-white text-2xl font-bold leading-none active:bg-brand-dark">+</button>
                </div>
                <div class="px-4 pb-2 flex flex-wrap gap-2 justify-center" id="portion-presets"></div>
                <div class="mx-4 mt-2 bg-slate-50 rounded-xl p-3 grid grid-cols-4 gap-2 text-center text-xs">
                    <div><div class="text-slate-400">热量</div><div class="font-bold text-slate-700 mt-0.5" id="pv-kcal">0</div></div>
                    <div><div class="text-blue-400">蛋白</div><div class="font-bold text-blue-700 mt-0.5" id="pv-p">0</div></div>
                    <div><div class="text-amber-500">碳水</div><div class="font-bold text-amber-700 mt-0.5" id="pv-c">0</div></div>
                    <div><div class="text-rose-400">脂肪</div><div class="font-bold text-rose-700 mt-0.5" id="pv-f">0</div></div>
                </div>
                <div class="mt-auto p-3 flex gap-2">
                    <button id="portion-back" class="flex-1 bg-slate-100 text-slate-600 font-bold py-3 rounded-xl">返回</button>
                    <button id="portion-add" class="flex-[2] bg-brand hover:bg-brand-dark text-white font-bold py-3 rounded-xl">加入这一餐</button>
                </div>
            </div>

            <div id="food-basket-wrap" class="border-t border-slate-100 p-3 bg-slate-50">'''
assert old_list in h, "food-list block not found"
h = h.replace(old_list, new_list, 1)

io.open(p,"w",encoding="utf-8",newline="\n").write(h)
print("html", orig, "->", len(h))
