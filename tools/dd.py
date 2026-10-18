import urllib.request as u, json
B="http://127.0.0.1:7788/api"
print("HEALTH:", u.urlopen(B+"/health",timeout=10).read().decode())
# 确认 debug 端点存在
r=u.Request(B+"/sync/debug",data=b"ping",method="POST",headers={"Content-Type":"text/plain"})
try:
    print("DEBUG:", json.loads(u.urlopen(r,timeout=10).read().decode()))
except u.HTTPError as e:
    print("DEBUG HTTP", e.code, e.read().decode()[:200])
