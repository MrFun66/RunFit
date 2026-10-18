import urllib.request as u, json
TOKEN="cfuM7wJuWU4J8X26D6wY6Xqn2C2o8Fmnn-cxUmpuj_E"
# 用「今天」范围 + 少量数据，模拟正常一次同步
payload={"data":{"metrics":[
  {"name":"step_count","units":"count","data":[{"date":"2026-10-18 12:00:00 +0800","qty":8888}]},
  {"name":"weight_body_mass","units":"kg","data":[{"date":"2026-10-18 07:00:00 +0800","qty":71.8}]},
]}}
r=u.Request("https://runfit.wenhh.top/api/sync/health",
  data=json.dumps(payload).encode(),method="POST",
  headers={"Authorization":"Bearer "+TOKEN,"User-Agent":"GRF/1.0","Content-Type":"application/json"})
print("[今天小包]", u.urlopen(r,timeout=60).read().decode())
