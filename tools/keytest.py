import urllib.request as u, json
TOKEN="cfuM7wJuWU4J8X26D6wY6Xqn2C2o8Fmnn-cxUmpuj_E"
URL="https://runfit.wenhh.top/api/sync/health"
def send(payload, label):
    r=u.Request(URL, data=json.dumps(payload,ensure_ascii=False).encode(), method="POST",
        headers={"Authorization":"Bearer "+TOKEN,"User-Agent":"GRF/1.0","Content-Type":"application/json"})
    try:
        print(label, "->", u.urlopen(r,timeout=60).read().decode()[:200])
    except u.HTTPError as e:
        print(label, "-> HTTP", e.code, e.read().decode()[:200])

# A: 键为空
send({"":"Date,Metric,Value,Unit\n2026-10-18 07:00:00 +0800,step_count,111,count"}, "[键为空]")
# B: 键=data，值是 CSV 字符串
send({"data":"Date,Metric,Value,Unit\n2026-10-18 07:00:00 +0800,step_count,222,count"}, "[键=data + CSV字符串]")
# C: 键=data，值是 HAE JSON 对象（导出锻炼的输出）
send({"data":{"workouts":[{"name":"Outdoor Run","start":"2026-10-18 07:00:00 +0800","duration":1800,"distance":{"qty":5.0,"units":"km"}}]}}, "[键=data + JSON对象]")
