import io
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
orig=len(h)

anchor = '<div class="mt-3 bg-rose-50 border border-rose-200 rounded-lg p-2.5">'
assert anchor in h, "anchor not found"

block = '''<div class="mt-3 bg-amber-50 border border-amber-300 rounded-lg p-2.5">
                        <div class="text-[11px] font-bold text-amber-800 mb-1">推荐：用 JSON 文本发，别用「文件」</div>
                        <div class="text-[11px] text-amber-900 leading-relaxed">
                            「请求体 = 文件」走的是 multipart，最容易报 <b>「网络连接已中断」</b>。改成文本发送稳定得多：<br>
                            1）在 HAE 动作里点 <b>「作为 CSV」</b> 右侧箭头 → 格式改成 <b>JSON</b>；<br>
                            2）「获取 URL 内容」→ <b>请求体</b> 选 <b>「文本」</b> → 点进输入框，插入上一步的变量；<br>
                            3）请求头保留 <b>Authorization</b> 那一行。<br>
                            <span class="text-amber-700">服务器对 JSON / CSV / 文件三种格式都支持，但 JSON 文本最不容易断。</span>
                        </div>
                    </div>

                    <div class="mt-2 bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                        <div class="text-[11px] font-bold text-slate-700 mb-1">发不出去时，先做这个 10 秒测试</div>
                        <div class="text-[11px] text-slate-600 leading-relaxed">
                            把 URL 临时改成 <code class="bg-white px-1 rounded">https://runfit.wenhh.top/api/sync/debug</code>，方法 POST，随便传点东西运行。<br>
                            能返回 JSON（里面有 <code>content_type</code>、<code>body_bytes</code>）说明网络和鉴权都没问题，问题只在格式；<br>
                            如果这里也报「网络连接已中断」，那就是 <b>URL 里有换行/空格</b>，请删掉重新粘贴一次。
                        </div>
                    </div>

                    '''
h = h.replace(anchor, block + anchor, 1)
io.open(p,"w",encoding="utf-8",newline="\n").write(h)
print("html", orig, "->", len(h))
