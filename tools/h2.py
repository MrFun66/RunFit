import urllib.request as u
try:
    print("HEALTH:", u.urlopen("http://127.0.0.1:7788/api/health",timeout=10).read().decode())
except Exception as e:
    print("ERR", e)
