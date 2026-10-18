import urllib.request as u, json, http.cookiejar, random
# 测试 raw CSV 文本（请求体=文本，内容就是CSV）
B="https://runfit.wenhh.top/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def jreq(p,d=None,m="POST"):
    body=json.dumps(d).encode() if d is not None else None
    return json.loads(op.open(u.Request(B+p,data=body,method=m,headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"}),timeout=60).read().decode())
un="rawcsv_%d"%random.randint(10000,99999)
jreq("/auth/register",{"username":un,"password":"pass1234"})
jreq("/auth/login",{"username":un,"password":"pass1234"})
tok=jreq("/sync/token",m="GET")["token"]
csv_text="Date,Metric,Value,Unit\n2026-10-18 07:00:00 +0800,step_count,6666,count\n"
r=u.Request(B+"/sync/health",data=csv_text.encode(),method="POST",
  headers={"Content-Type":"text/csv","Authorization":"Bearer "+tok,"User-Agent":"Shortcuts/1200 CFNetwork/1568.100.1"})
print("[raw CSV text]", json.loads(u.urlopen(r,timeout=60).read().decode()))
