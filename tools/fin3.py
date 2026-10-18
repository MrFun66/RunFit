import urllib.request as u, json, http.cookiejar, datetime, random
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def req(p,d=None,m="POST"):
    body=json.dumps(d).encode() if d is not None else None
    r=u.Request(B+p,data=body,method=m,headers={"Content-Type":"application/json"})
    return json.loads(op.open(r,timeout=30).read().decode())
def get(p): return json.loads(op.open(u.Request(B+p),timeout=30).read().decode())
un="one_%d"%random.randint(10000,99999)
req("/auth/register",{"username":un,"password":"pass1234"})
req("/auth/login",{"username":un,"password":"pass1234"})
req("/profile",{"sex":"male","birth_year":1998,"height_cm":178,"weight_kg":72,"bodyfat_pct":16,"goal":"recomp","activity_level":"moderate","training_days_per_week":4},"PUT")
today=datetime.date.today().isoformat()
req("/body",{"date":today,"weight_kg":72,"bodyfat_pct":16})
d=get("/meals"); print("[0] 空: items=",len(d["items"]),"target?",bool(d["target"]))
req("/meals/from-foods",{"date":today,"slot":"breakfast","items":[{"name":"燕麦片（干）","grams":60},{"name":"鸡蛋","grams":100}]})
d=get("/meals")
print("[1] 只记早餐: items=",len(d["items"]),"target?",bool(d["target"]),"meals_complete=",d["meals_complete"])
print("    total=",d["total"])
print("    target=",d["target"])
print("    => 前端条件(hasAny && tgt) =", bool(d["items"]) and bool(d["target"]))
