import io
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
orig=len(h)

anchor = '<div class="mt-3 bg-amber-50 border border-amber-300 rounded-lg p-2.5">'
assert anchor in h

block = '''<div class="mt-3 bg-rose-50 border-2 border-rose-400 rounded-lg p-3">
                        <div class="text-[12px] font-bold text-rose-700 mb-1.5">⚠️ 必加：User-Agent 请求头</div>
                        <div class="text-[11px] text-rose-800 leading-relaxed">
                            如果报 <b>「网络连接已中断」</b>，99% 是因为请求没有 User-Agent，被 Cloudflare 直接拦掉（服务器根本收不到）。<br><br>
                            在每个「获取 URL 内容」的 <b>头部</b> 里点 <b>+</b> 添加：<br>
                            <code class="bg-white px-1.5 py-0.5 rounded border border-rose-200 inline-block mt-1">键：User-Agent</code><br>
                            <code class="bg-white px-1.5 py-0.5 rounded border border-rose-200 inline-block mt-1">值：GRF/1.0</code><br><br>
                            <span class="text-rose-700">值随便写，非空即可。加完这一条就能通。</span>
                        </div>
                    </div>

                    '''
h = h.replace(anchor, block + anchor, 1)
io.open(p,"w",encoding="utf-8",newline="\n").write(h)
print("html", orig, "->", len(h))
