import io
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
old='<span id="mac-badge" class="text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">未满三餐</span>'
new='<span id="mac-badge" class="text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">未记录</span>'
assert old in h
h=h.replace(old,new,1)
io.open(p,"w",encoding="utf-8",newline="\n").write(h)
print("badge default -> 未记录")
