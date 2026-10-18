import urllib.request as u
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
# 公网 debug 端点测试
r=u.Request("https://runfit.wenhh.top/api/sync/debug",data=b"hello-from-public",method="POST",headers={"Content-Type":"text/plain","User-Agent":UA["User-Agent"]})
try:
    print("PUBLIC DEBUG:", u.urlopen(r,timeout=30).read().decode())
except Exception as e:
    print("ERR", e)
