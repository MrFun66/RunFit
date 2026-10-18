import io
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
orig=len(h)

old = '''<div class="font-bold text-slate-700 mb-1">4. 加两个「获取 URL 内容」把数据发给我们</div>
                                <b>第一个</b>：URL 粘贴<b>推送地址</b>，方法 <b>POST</b>，请求体选<b>「批量导出健康指标」</b>的输出；<br>'''

new = '''<div class="font-bold text-slate-700 mb-1">4. 加「获取 URL 内容」把数据发给我们</div>
                                <span class="text-amber-700">注意：这个动作是<b>苹果自带的</b>，不在 HAE 里。点「+」后<b>清空搜索框</b>，重新搜 <b>URL</b> 或 <b>获取</b>，就能看到<b>「获取 URL 内容」</b>（英文 Get Contents of URL）。</span><br><br>
                                <b>第一个</b>：URL 粘贴<b>推送地址</b>，方法 <b>POST</b>，请求体选<b>「批量导出健康指标」</b>的输出；<br>'''

assert old in h, "step4 not found"
h = h.replace(old, new, 1)

# 第2步也补一句：HAE 动作搜 auto
old2 = '''搜索 <b>Health Auto Export</b>，添加动作 <b>「批量导出健康指标」</b>。<br>'''
new2 = '''搜索 <b>auto</b> 或 <b>Health Auto Export</b>，在 HAE 的动作里选 <b>「批量导出健康指标」</b>。<br>'''
assert old2 in h
h = h.replace(old2, new2, 1)

io.open(p,"w",encoding="utf-8",newline="\n").write(h)
print("html", orig, "->", len(h))
