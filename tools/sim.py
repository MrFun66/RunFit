import urllib.request as u, json
TOKEN = "cfuM7wJuWU4J8X26D6wY6Xqn2C2o8Fmnn-cxUmpuj_E"
# 模拟用户当前的做法：请求体 JSON，一个字段，值是「导出锻炼」的输出
payload = {"导出锻炼": "Date,Metric,Value,Unit\n2026-10-18 07:00:00 +0800,step_count,1234,count"}
r = u.Request("https://runfit.wenhh.top/api/sync/health",
    data=json.dumps(payload, ensure_ascii=False).encode(), method="POST",
    headers={"Authorization":"Bearer "+TOKEN, "User-Agent":"GRF/1.0",
             "Content-Type":"application/json"})
try:
    print("[当前 JSON 结构]", u.urlopen(r, timeout=30).read().decode())
except u.HTTPError as e:
    print("[当前 JSON 结构] HTTP", e.code, e.read().decode()[:300])
