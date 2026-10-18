import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find("为什么不能一键装快捷指令")
print("idx",i)
print(h[i-1200:i+900])
