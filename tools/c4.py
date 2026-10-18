import io
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
orig=len(h)

start_marker = '<div class="mt-3 bg-emerald-50 border border-emerald-200 rounded-lg p-2.5">'
end_marker = '<details class="mt-2">\n                        <summary class="text-xs text-slate-400 cursor-pointer">为什么不能直接点一下装好？</summary>'

i = h.find(start_marker)
j = h.find(end_marker)
assert i > 0 and j > i, (i, j)

new_block = '''<div class="mt-3 bg-emerald-50 border border-emerald-200 rounded-lg p-2.5">
                        <div class="text-[11px] font-bold text-emerald-700 mb-1">免费版就够用</div>
                        <div class="text-[11px] text-emerald-800 leading-relaxed">
                            Health Auto Export 免费版自带<b>「快捷指令」动作</b>，一次能导出<b>全部健康指标 + 锻炼</b>。<br>
                            在手机上建一次，之后每天自动跑，<b>永久免费，不用订阅</b>。
                        </div>
                    </div>

                    <details class="mt-3" open>
                        <summary class="text-xs text-brand cursor-pointer font-bold">4 步建好（只需一次，之后全自动）</summary>
                        <div class="text-xs text-slate-500 mt-2 leading-relaxed space-y-2">
                            <div class="bg-slate-50 rounded-lg p-2.5">
                                <div class="font-bold text-slate-700 mb-1">1. 点上面「生成我的配置」</div>
                                拿到<b>推送地址</b>和<b>请求头</b>，各点一次「复制」。
                            </div>
                            <div class="bg-slate-50 rounded-lg p-2.5">
                                <div class="font-bold text-slate-700 mb-1">2. 快捷指令 App → 右上角 + 新建</div>
                                搜 <b>Health Auto Export</b>，添加 <b>Export Health Data（导出健康数据）</b> 动作。<br>
                                <span class="text-slate-500">里面选 <b>All Health Metrics</b> 一键全选（睡眠/心率/HRV/步数/VO2Max/体重/体脂…），把 <b>Workouts</b> 也打开。不用逐个勾。</span>
                            </div>
                            <div class="bg-slate-50 rounded-lg p-2.5">
                                <div class="font-bold text-slate-700 mb-1">3. 再加一个「获取 URL 内容」</div>
                                URL 粘贴上面的<b>推送地址</b>，方法选 <b>POST</b>；<br>
                                请求头加一项 <b>Authorization</b>，值是<b>请求头</b>里 <code>Bearer</code> 后面那一整串（含 <code>Bearer </code> 一起复制即可）；<br>
                                请求体选上一步的输出（若它给的是文件，先加一个「获取文件内容」再传）。
                            </div>
                            <div class="bg-slate-50 rounded-lg p-2.5">
                                <div class="font-bold text-emerald-700 mb-1">4. 设个人自动化，每天定时跑</div>
                                快捷指令 App → <b>自动化</b> → 新建 → <b>时间</b> → 每天 8:00 → 运行上面这个快捷指令，并关掉「运行前询问」。<br>
                                <span class="text-slate-500">先手动点一次运行，回到本页刷新，能看到数据就说明通了。</span>
                            </div>
                            <div class="text-[11px] text-slate-400">
                                这条路完全免费，且因为是你自己在手机上建的动作，不受「未签名快捷指令」限制。
                            </div>
                        </div>
                    </details>

                    '''
h = h[:i] + new_block + h[j:]
io.open(p,"w",encoding="utf-8",newline="\n").write(h)
print("html", orig, "->", len(h))
for k in ["路线 A","前 7 天","REST API","4 步建好","All Health Metrics","免费版就够用"]:
    print("  ", k, k in h)
