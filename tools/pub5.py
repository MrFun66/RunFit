import urllib.request as u, json
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
print("LOCAL health:", u.urlopen("http://127.0.0.1:7788/api/health",timeout=10).read().decode())
b=u.urlopen(u.Request("https://runfit.wenhh.top/",headers=UA),timeout=30).read().decode("utf-8","ignore")
print("PUBLIC index len", len(b))
for k in ["批量导出健康指标","导出锻炼","5 步建好","获取 URL 内容","Authorization","免费版就够用"]:
    print("  ", k, k in b)
# 配置接口抽查
import http.cookiejar, random
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
un="cfgchk_%d"%random.randint(1000,9999)
op.open(u.Request(B+"/auth/register",data=json.dumps({"username":un,"password":"pass1234"}).encode(),headers={"Content-Type":"application/json"}))
op.open(u.Request(B+"/auth/login",data=json.dumps({"username":un,"password":"pass1234"}).encode(),headers={"Content-Type":"application/json"}))
cfg=json.loads(op.open(B+"/sync/config").read().decode())
print("CONFIG endpoint:", cfg.get("endpoint"))
print("CONFIG header  :", (cfg.get("header") or "")[:32]+"...")
