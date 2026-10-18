import urllib.request as u
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
b=u.urlopen(u.Request("https://runfit.wenhh.top/",headers=UA),timeout=30).read().decode("utf-8","ignore")
print("PUBLIC index len",len(b))
for k in ["记录任意一餐后","food-portion","portion-grams","portion-presets","pv-kcal","未记录"]:
    print("  ",k, k in b)
