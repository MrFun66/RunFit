import urllib.request as u, uuid
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
# 直接对公网 debug 发 multipart（模拟快捷指令请求体=文件）
boundary="----D"+uuid.uuid4().hex
body=b"\r\n".join([
  ("--"+boundary).encode(),
  b'Content-Disposition: form-data; name="file"; filename="t.csv"',
  b"Content-Type: text/csv", b"", b"a,b,c\n1,2,3\n",
  ("--"+boundary+"--").encode(), b""
])
h={"User-Agent":UA["User-Agent"],"Content-Type":"multipart/form-data; boundary="+boundary}
r=u.Request("https://runfit.wenhh.top/api/sync/debug",data=body,method="POST",headers=h)
print("[公网 debug multipart]", u.urlopen(r,timeout=60).read().decode()[:400])
