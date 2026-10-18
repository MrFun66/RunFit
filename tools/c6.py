import io
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
orig=len(h)

# 1) 顶部描述
old1 = '免费版没有「服务器」自动化，但有「快捷指令」。下面两条路任选一条，都能把跑步/睡眠/心率/体重/步数/HRV 全部一次性同步过来。'
new1 = '免费版没有「服务器」自动化，但自带「快捷指令」动作。用下面的方法建一次，跑步/睡眠/心率/体重/步数/HRV 全部一次性同步过来，之后每天自动跑。'
assert old1 in h, "top desc not found"
h = h.replace(old1, new1, 1)

# 2) 底部解释里的路线提法
old2 = '所以只能手动建一次（路线 B），或者用 App 的 REST API（路线 A）。'
new2 = '所以只能自己在手机上手动建一次（就是上面的 4 步），一次建好永久有效。'
assert old2 in h, "footer route text not found"
h = h.replace(old2, new2, 1)

io.open(p,"w",encoding="utf-8",newline="\n").write(h)
print("html", orig, "->", len(h))
for k in ["路线 A","路线 B","两条路","前 7 天","REST API","服务器"]:
    print("  ", k, k in h)
