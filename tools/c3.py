import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('iPhone 健康同步')
j=h.find('</details>', h.find('为什么不能一键装快捷指令', i))
print(h[i-200:j+320])
