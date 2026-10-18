# 验证后端能接收「只有 workouts」和「只有 metrics」两种单独 payload
import urllib.request as u, json, random
B="http://127.0.0.1:7788/api"
def post(p,d,hdr=None):
    h={"Content-Type":"application/json"}
    if hdr: h.update(hdr)
    r=u.Request(B+p,data=json.dumps(d).encode(),headers=h)
    try:
        return 200, json.loads(u.urlopen(r,timeout=30).read().decode())
    except u.HTTPError as e:
        return e.code, e.read().decode()[:200]
# 注册并拿 token
un="fmt_%d"%random.randint(10000,99999)
print(post("/auth/register",{"username":un,"password":"pass1234"}))
# 用 sync token 直接测
import http.cookiejar
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
op.open(u.Request(B+"/auth/login",data=json.dumps({"username":un,"password":"pass1234"}).encode(),headers={"Content-Type":"application/json"}))
tok=json.loads(op.open(B+"/sync/token").read().decode())["token"]
H={"Authorization":"Bearer "+tok}

only_metrics={"data":{"metrics":[{"name":"step_count","units":"count","data":[{"date":"2026-10-18 00:00:00 +0800","qty":9000}]}]}}
only_workouts={"data":{"workouts":[{"name":"Outdoor Run","start":"2026-10-18 07:00:00 +0800","end":"2026-10-18 07:30:00 +0800","duration":1800,"distance":{"qty":5.0,"units":"km"}}]}}
print("only metrics :", post("/sync/health", only_metrics, H))
print("only workouts:", post("/sync/health", only_workouts, H))
