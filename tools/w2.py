# 测试大 CSV（模拟 103 指标 × 1 天，约 5000 行）能否在 30s 内处理完
import urllib.request as u, json, http.cookiejar, random, uuid, time
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def jreq(p,d=None,m="POST"):
    body=json.dumps(d).encode() if d is not None else None
    return json.loads(op.open(u.Request(B+p,data=body,method=m,headers={"Content-Type":"application/json"}),timeout=60).read().decode())
un="big_%d"%random.randint(10000,99999)
jreq("/auth/register",{"username":un,"password":"pass1234"})
jreq("/auth/login",{"username":un,"password":"pass1234"})
tok=jreq("/sync/token")["token"]

# 生成 5000 行长表 CSV
lines=["Date,Metric,Value,Unit"]
for i in range(5000):
    lines.append("2026-10-18 %02d:%02d:00 +0800,step_count,%d,count" % (i%24, i%60, 1000+i))
csv_text="\n".join(lines)
data=csv_text.encode()

boundary="----B"+uuid.uuid4().hex
body=b"\r\n".join([
  ("--"+boundary).encode(),
  b'Content-Disposition: form-data; name="file"; filename="big.csv"',
  b"Content-Type: text/csv",
  b"",
  data,
  ("--"+boundary+"--").encode(), b""
])
t0=time.time()
r=u.Request(B+"/sync/health",data=body,method="POST",headers={
  "Content-Type":"multipart/form-data; boundary="+boundary,
  "Authorization":"Bearer "+tok})
res=json.loads(op.open(r,timeout=180).read().decode())
el=time.time()-t0
print("rows 5000 ->", res)
print("耗时 %.2fs  体积 %.1f KB" % (el, len(body)/1024))
