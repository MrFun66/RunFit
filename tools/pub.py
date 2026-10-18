import urllib.request as u
UA={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
for url,keys in [("https://runfit.wenhh.top/",["btn-open-food","macro-locked","macro-body","mac-kcal-t","食物库","拍照识餐"]),
                 ("https://runfit.wenhh.top/assets/app.js",["openFoodModal","initFoodModal","_renderBasket","meals_complete","mac-daytype"])]:
    try:
        b=u.urlopen(u.Request(url,headers=UA),timeout=30).read().decode("utf-8","ignore")
        print(url, "len", len(b))
        for k in keys: print("   ",k, k in b)
    except Exception as e:
        print(url,"ERR",e)
