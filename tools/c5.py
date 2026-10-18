import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('iPhone 健康同步')
j=h.find('</details>', h.find('为什么不能直接点一下装好', i))
print(h[i-120:j+200])
print("--- details open:", h.count('<details class="mt-3" open>'), "close:", h.count('</details>'))
