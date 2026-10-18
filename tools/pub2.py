import urllib.request as u
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
for url,keys in [("https://runfit.wenhh.top/",["food-portion","portion-grams","portion-add","已记录任意一餐","macro-body"]),
                 ("https://runfit.wenhh.top/assets/app.js",["openPortion","initPortionPanel","_updatePortionPreview","hasAny"])]:
    try:
        b=u.urlopen(u.Request(url,headers=UA),timeout=30).read().decode("utf-8","ignore")
        print(url,"len",len(b))
        for k in keys: print("   ",k, k in b)
    except Exception as e: print(url,"ERR",e)
