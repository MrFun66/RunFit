import urllib.request as u, json, http.cookiejar, random
B="https://runfit.wenhh.top/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def jreq(p,d=None,m="POST"):
    body=json.dumps(d).encode() if d is not None else None
    return json.loads(op.open(u.Request(B+p,data=body,method=m,headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"}),timeout=60).read().decode())
un="qtok_%d"%random.randint(10000,99999)
jreq("/auth/register",{"username":un,"password":"pass1234"})
jreq("/auth/login",{"username":un,"password":"pass1234"})
tok=jreq("/sync/token",m="GET")["token"]

# 1) token 放 URL 查询参数，不带 Authorization 头
csv_text="Date,Metric,Value,Unit\n2026-10-18 07:00:00 +0800,step_count,5555,count\n"
url = B + "/sync/health?token=" + tok
r = u.Request(url, data=csv_text.encode(), method="POST",
              headers={"Content-Type":"text/csv","User-Agent":"GRF/1.0"})
print("[query token + csv]", json.loads(u.urlopen(r,timeout=60).read().decode()))

# 2) token 放 URL + multipart 文件
import uuid
boundary="----Q"+uuid.uuid4().hex
body=b"\r\n".join([("--"+boundary).encode(),
  b'Content-Disposition: form-data; name="file"; filename="a.csv"',
  b"Content-Type: text/csv", b"", csv_text.encode(),
  ("--"+boundary+"--").encode(), b""])
r2 = u.Request(url, data=body, method="POST",
               headers={"Content-Type":"multipart/form-data; boundary="+boundary,"User-Agent":"GRF/1.0"})
print("[query token + file]", json.loads(u.urlopen(r2,timeout=60).read().decode()))
