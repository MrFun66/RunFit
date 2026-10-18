# 用公网域名跑一次小 CSV，确认公网链路通
import urllib.request as u, json, http.cookiejar, random, uuid
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1","Content-Type":"application/json"}
B="https://runfit.wenhh.top/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def jreq(p,d=None,m="POST"):
    body=json.dumps(d).encode() if d is not None else None
    return json.loads(op.open(u.Request(B+p,data=body,method=m,headers=UA),timeout=60).read().decode())
un="pubcsv_%d"%random.randint(10000,99999)
jreq("/auth/register",{"username":un,"password":"pass1234"})
jreq("/auth/login",{"username":un,"password":"pass1234"})
tok=jreq("/sync/token",m="GET")["token"]
csv_text="Date,Metric,Value,Unit\n2026-10-18 07:00:00 +0800,step_count,8888,count\n2026-10-18 07:10:00 +0800,weight_body_mass,71.5,kg\n"
boundary="----P"+uuid.uuid4().hex
body=b"\r\n".join([("--"+boundary).encode(),
  b'Content-Disposition: form-data; name="file"; filename="m.csv"',
  b"Content-Type: text/csv", b"", csv_text.encode(),
  ("--"+boundary+"--").encode(), b""])
h=dict(UA); h["Authorization"]="Bearer "+tok
h["Content-Type"]="multipart/form-data; boundary="+boundary
r=u.Request(B+"/sync/health",data=body,method="POST",headers=h)
print("[公网 CSV 上传]", json.loads(op.open(r,timeout=60).read().decode()))
