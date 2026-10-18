import io
h=io.open("web/index.html",encoding="utf-8").read()
i=h.find('iPhone 健康同步')
# 找卡片 div 起止
start=h.rfind('<div', 0, i-200)
# 简单取到下一个 details 结束后的第一个 </div> 层级不好算，直接打印范围
print("start", start, "i", i)
seg=h[i-500:i+300]
print(seg)
