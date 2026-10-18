import urllib.request as u
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
for url in ["https://runfit.wenhh.top/","https://runfit.wenhh.top/assets/app.js"]:
    try:
        r=u.urlopen(u.Request(url,headers=UA),timeout=25)
        b=r.read().decode("utf-8","ignore")
        print(url,r.status,len(b))
        if url.endswith("/"):
            for k in ["btn-sync-config","cfg-endpoint","cfg-header","Health Auto Export","All Health Metrics","btn-install-shortcut"]:
                print("  ",k,k in b)
        else:
            for k in ["loadSyncConfig","initSyncCard","installShortcut"]:
                print("  ",k,k in b)
    except Exception as e:
        print(url,"ERR",e)
