import urllib.request as u, uuid, json
# 模拟 iOS 快捷指令的 UA
UAS = [
  ("Shortcuts", "Shortcuts/1200 CFNetwork/1568.100.1 Darwin/24.0.0"),
  ("CFNetwork", "App/1 CFNetwork/1568.100.1 Darwin/24.0.0"),
  ("empty", ""),
]
for name, ua in UAS:
    h={"Content-Type":"text/plain"}
    if ua: h["User-Agent"]=ua
    r=u.Request("https://runfit.wenhh.top/api/sync/debug",data=b"test-"+name.encode(),method="POST",headers=h)
    try:
        res=u.urlopen(r,timeout=30).read().decode()[:160]
        print(name,"->",res)
    except Exception as e:
        print(name,"-> ERR",type(e).__name__,e)
