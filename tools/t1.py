import urllib.request as u, json, http.cookiejar, random, uuid
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def jreq(p,d=None,m="POST"):
    body=json.dumps(d).encode() if d is not None else None
    return json.loads(op.open(u.Request(B+p,data=body,method=m,headers={"Content-Type":"application/json"}),timeout=30).read().decode())
un="csv_%d"%random.randint(10000,99999)
jreq("/auth/register",{"username":un,"password":"pass1234"})
jreq("/auth/login",{"username":un,"password":"pass1234"})
tok=jreq("/sync/token")["token"]

# 模拟 HAE「批量导出健康指标」长表 CSV
csv_text = "Date,Metric,Value,Unit\n2026-10-18 00:00:00 +0800,step_count,9123,count\n2026-10-18 07:00:00 +0800,sleep_analysis,7.4,hr\n2026-10-18 07:10:00 +0800,weight_body_mass,72.1,kg\n2026-10-18 07:20:00 +0800,heart_rate_variability,48,ms\n"
data = csv_text.encode("utf-8")

# 构造 multipart/form-data，字段名 file（模拟快捷指令「请求体=文件」）
boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
parts = []
parts.append(("--"+boundary).encode())
parts.append(b'Content-Disposition: form-data; name="file"; filename="HealthMetrics.csv"')
parts.append(b"Content-Type: text/csv")
parts.append(b"")
parts.append(data)
parts.append(("--"+boundary+"--").encode())
parts.append(b"")
body = b"\r\n".join(parts)

r = u.Request(B+"/sync/health", data=body, method="POST", headers={
    "Content-Type": "multipart/form-data; boundary="+boundary,
    "Authorization": "Bearer "+tok,
})
print("[multipart CSV]", json.loads(op.open(r,timeout=40).read().decode()))
print("[samples]", json.loads(op.open(B+"/sync/samples?days=30").read().decode()).get("metrics"))
