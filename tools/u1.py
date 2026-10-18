import io
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
orig=len(h)

old = '''<span class="text-amber-600">如果动作输出的是<b>文件</b>，先各加一个「获取文件内容」转成文本，再传给「获取 URL 内容」。</span>'''
new = '''<span class="text-emerald-600">请求体选 <b>「文件」</b> 就行（HAE 默认导出 CSV），服务器会自动识别 CSV，<b>不用改格式</b>。</span><br>
                                <span class="text-slate-500">两个「获取 URL 内容」都要加 <b>Authorization</b> 头部。第一个传「批量导出健康指标」，第二个传「导出锻炼」。</span>'''
assert old in h, "step4 tip not found"
h = h.replace(old, new, 1)

# 第2步补一句：范围选「今天」
old2 = '''点动作里的<b>「今天」</b>（或「过去 7 天」）。这个动作一次性包含睡眠/心率/HRV/步数/VO2Max/体重/体脂等全部指标，<b>不用逐个选</b>。'''
new2 = '''点动作里的<b>「今天」</b>（或「过去 7 天」）。这个动作一次性包含睡眠/心率/HRV/步数/VO2Max/体重/体脂等全部指标，<b>不用逐个选</b>。<br>
                                <span class="text-amber-600">注意：范围不要选「昨天」——选「今天」才能同步到当天数据。</span>'''
assert old2 in h
h = h.replace(old2, new2, 1)

io.open(p,"w",encoding="utf-8",newline="\n").write(h)
print("html", orig, "->", len(h))
