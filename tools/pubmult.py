import urllib.request as u, json, http.cookiejar, random, uuid
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1","Content-Type":"application/json"}
B="https://runfit.wenhh.top/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def jreq(p,d=None,m="POST"):
    body=json.dumps(d).encode() if d is not None else None
    return json.loads(op.open(u.Request(B+p,data=body,method=m,headers=UA),timeout=60).read().decode())
un="pubf_%d"%random.randint(10000,99999)
jreq("/auth/register",{"username":un,"password":"pass1234"})
jreq("/auth/login",{"username":un,"password":"pass1234"})
tok=jreq("/sync/token",m="GET")["token"]

csv_text="Date,Metric,Value,Unit\n2026-10-18 07:00:00 +0800,step_count,8888,count\n2026-10-18 07:10:00 +0800,weight_body_mass,71.5,kg\n"
boundary="----P"+uuid.uuid4().hex
body=b"\r\n".join([
  ("--"+boundary).encode(),
  b'Content-Disposition: form-data; name="file"; filename="HealthMetrics.csv"',
  b"Content-Type: text/csv", b"", csv_text.encode(),
  ("--"+boundary+"--").encode(), b""
])
h={"User-Agent":UA["User-Agent"],"Authorization":"Bearer "+tok,
   "Content-Type":"multipart/form-data; boundary="+boundary}
try:
    r=u.Request(B+"/sync/health",data=body,method="POST",headers=h)
    print("[公网 multipart CSV]", json.loads(u.urlopen(r,timeout=90).read().decode()))
except Exception as e:
    print("[公网 multipart 失败]", type(e).__name__, e)
