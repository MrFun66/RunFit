import urllib.request as u, json
# 模拟「请求体=文本」发 JSON：Content-Type: text/plain
B="http://127.0.0.1:7788/api"
import http.cookiejar, random
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def j(p,d=None,m="POST"):
    body=json.dumps(d).encode() if d is not None else None
    return json.loads(op.open(u.Request(B+p,data=body,method=m,headers={"Content-Type":"application/json"}),timeout=30).read().decode())
un="txt_%d"%random.randint(10000,99999)
j("/auth/register",{"username":un,"password":"pass1234"})
j("/auth/login",{"username":un,"password":"pass1234"})
tok=j("/sync/token",m="GET")["token"]

payload={"data":{"metrics":[{"name":"step_count","units":"count","data":[{"date":"2026-10-18 08:00:00 +0800","qty":7777}]}]}}
r=u.Request(B+"/sync/health",data=json.dumps(payload).encode(),method="POST",
            headers={"Content-Type":"text/plain","Authorization":"Bearer "+tok})
print("[text/plain JSON]", json.loads(op.open(r,timeout=30).read().decode()))

# debug 端点
r2=u.Request(B+"/sync/debug",data=b"hello",method="POST",headers={"Content-Type":"text/plain","Authorization":"Bearer "+tok})
print("[debug]", json.loads(op.open(r2,timeout=30).read().decode()))
