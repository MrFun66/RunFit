import io
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
orig=len(h)

# 定位 4 步建好 这个 details 块
start = h.find('<summary class="text-xs text-brand cursor-pointer font-bold">4 步建好')
assert start > 0
blk_start = h.rfind('<details', 0, start)
blk_end = h.find('</details>', start) + len('</details>')
assert blk_start > 0 and blk_end > blk_start

new_block = '''<details class="mt-3" open>
                        <summary class="text-xs text-brand cursor-pointer font-bold">5 步建好（只需一次，之后全自动）</summary>
                        <div class="text-xs text-slate-500 mt-2 leading-relaxed space-y-2">
                            <div class="bg-slate-50 rounded-lg p-2.5">
                                <div class="font-bold text-slate-700 mb-1">1. 点上面「生成我的配置」</div>
                                拿到<b>推送地址</b>和<b>请求头</b>，各点一次「复制」。
                            </div>
                            <div class="bg-slate-50 rounded-lg p-2.5">
                                <div class="font-bold text-slate-700 mb-1">2. 快捷指令 App → 右上角 + → 新建</div>
                                搜索 <b>Health Auto Export</b>，添加动作 <b>「批量导出健康指标」</b>。<br>
                                点动作里的<b>「今天」</b>（或「过去 7 天」）。这个动作一次性包含睡眠/心率/HRV/步数/VO2Max/体重/体脂等全部指标，<b>不用逐个选</b>。
                            </div>
                            <div class="bg-slate-50 rounded-lg p-2.5">
                                <div class="font-bold text-slate-700 mb-1">3. 再加「导出锻炼」动作</div>
                                同样搜 <b>Health Auto Export</b>，添加 <b>「导出锻炼」</b>，范围也选<b>「今天」</b>。<br>
                                <span class="text-slate-500">这样跑步/骑行/力量训练记录也会一起上来。</span>
                            </div>
                            <div class="bg-slate-50 rounded-lg p-2.5">
                                <div class="font-bold text-slate-700 mb-1">4. 加两个「获取 URL 内容」把数据发给我们</div>
                                <b>第一个</b>：URL 粘贴<b>推送地址</b>，方法 <b>POST</b>，请求体选<b>「批量导出健康指标」</b>的输出；<br>
                                请求头加一项 <b>Authorization</b>，值粘贴<b>请求头</b>（含 <code>Bearer </code>）。<br>
                                <b>第二个</b>：同样 URL 和方法，请求体选<b>「导出锻炼」</b>的输出，请求头同上。<br>
                                <span class="text-amber-600">如果动作输出的是<b>文件</b>，先各加一个「获取文件内容」转成文本，再传给「获取 URL 内容」。</span>
                            </div>
                            <div class="bg-slate-50 rounded-lg p-2.5">
                                <div class="font-bold text-emerald-700 mb-1">5. 设个人自动化，每天定时跑</div>
                                快捷指令 App → <b>自动化</b> → 新建 → <b>时间</b> → 每天 8:00 → 运行上面这个快捷指令，关掉「运行前询问」。<br>
                                <span class="text-slate-500">先手动点一次运行，回到本页刷新，能看到数据就说明通了。</span>
                            </div>
                            <div class="text-[11px] text-slate-400">
                                这条路完全免费。因为是你自己在手机上建的动作，不受「未签名快捷指令」限制。
                            </div>
                        </div>
                    </details>'''

h = h[:blk_start] + new_block + h[blk_end:]
io.open(p,"w",encoding="utf-8",newline="\n").write(h)
print("html", orig, "->", len(h))
for k in ["批量导出健康指标","导出锻炼","导出健康数据","5 步建好"]:
    print("  ", k, k in h)
