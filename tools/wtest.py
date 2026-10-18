import urllib.request as u, json
TOKEN="cfuM7wJuWU4J8X26D6wY6Xqn2C2o8Fmnn-cxUmpuj_E"
# 模拟你截图里的 JSON 单字段包 CSV
payload={"导出锻炼":"Date,Metric,Value,Unit\n2026-10-18 07:00:00 +0800,step_count,4321,count\n"}
r=u.Request("https://runfit.wenhh.top/api/sync/health",
  data=json.dumps(payload,ensure_ascii=False).encode(),method="POST",
  headers={"Authorization":"Bearer "+TOKEN,"User-Agent":"GRF/1.0","Content-Type":"application/json"})
print("[JSON包CSV]", u.urlopen(r,timeout=60).read().decode())
