import urllib.request as u
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
b=u.urlopen(u.Request("https://runfit.wenhh.top/",headers=UA),timeout=30).read().decode("utf-8","ignore")
print("PUBLIC len",len(b))
for k in ["网络连接已中断","超时调到","批量导出健康指标","分开单独运行","今天"]:
    print("  ",k, k in b)
