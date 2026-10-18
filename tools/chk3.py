import urllib.request as u, uuid
TOKEN="cfuM7wJuWU4J8X26D6wY6Xqn2C2o8Fmnn-cxUmpuj_E"
# 正确格式：multipart + 真实 CSV + 正确的头
csv="Date,Metric,Value,Unit\n2026-10-18 07:00:00 +0800,step_count,9999,count\n2026-10-18 07:10:00 +0800,weight_body_mass,71.8,kg\n"
b="----V"+uuid.uuid4().hex
body=b"\r\n".join([("--"+b).encode(),
  b'Content-Disposition: form-data; name="file"; filename="HealthMetrics.csv"',
  b"Content-Type: text/csv", b"", csv.encode(),
  ("--"+b+"--").encode(), b""])
r=u.Request("https://runfit.wenhh.top/api/sync/health",data=body,method="POST",headers={
  "Authorization":"Bearer "+TOKEN, "User-Agent":"GRF/1.0",
  "Content-Type":"multipart/form-data; boundary="+b})
print("[正确格式上传]", u.urlopen(r,timeout=60).read().decode())
