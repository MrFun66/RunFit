import urllib.request as u, json
print(u.urlopen("http://127.0.0.1:7788/api/health",timeout=10).read().decode())
