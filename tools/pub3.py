import urllib.request as u
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
b=u.urlopen(u.Request("https://runfit.wenhh.top/",headers=UA),timeout=30).read().decode("utf-8","ignore")
for k in ["记录任意一餐后","已摄入 / 建议","macro-locked","macro-body","已摄入 / 建议 ·"]:
    print(k, k in b)
i=b.find('id="macro-locked"')
print("--- macro-locked block ---")
print(b[i-160:i+320])
