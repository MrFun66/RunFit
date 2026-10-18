import io
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
orig=len(h)

# 在 5 步说明前插入「排错」提示
anchor = '<details class="mt-3" open>\n                        <summary class="text-xs text-brand cursor-pointer font-bold">5 步建好（只需一次，之后全自动）</summary>'
assert anchor in h, "anchor not found"

tip = '''<div class="mt-3 bg-rose-50 border border-rose-200 rounded-lg p-2.5">
                        <div class="text-[11px] font-bold text-rose-700 mb-1">如果提示「网络连接已中断」</div>
                        <div class="text-[11px] text-rose-800 leading-relaxed">
                            多半是<b>数据量太大或上传超时</b>。按顺序试：<br>
                            1）动作范围改成 <b>「今天」</b>，不要选「昨天 / 过去 7 天」；<br>
                            2）把两个「获取 URL 内容」<b>分开单独运行</b>（先只跑健康指标，再跑锻炼）；<br>
                            3）快捷指令里给「获取 URL 内容」加长超时：点动作右下角 <b>ⓘ</b> → 打开「显示更多」→ 把超时调到 <b>120 秒</b>。
                        </div>
                    </div>

                    '''
h = h.replace(anchor, tip + anchor, 1)
io.open(p,"w",encoding="utf-8",newline="\n").write(h)
print("html", orig, "->", len(h))
