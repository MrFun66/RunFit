import urllib.request as u, json, http.cookiejar, datetime, random
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def post(p,d=None):
    body=json.dumps(d).encode() if d is not None else b""
    return json.loads(op.open(u.Request(B+p,data=body,headers={"Content-Type":"application/json"}),timeout=30).read().decode())
def get(p): return json.loads(op.open(u.Request(B+p),timeout=30).read().decode())
un="one_%d"%random.randint(10000,99999)
post("/auth/register",{"username":un,"password":"pass1234"}); post("/auth/login",{"username":un,"password":"pass1234"})
post("/profile",{"sex":"male","birth_year":1998,"height_cm":178,"weight_kg":72,"bodyfat_pct":16,"goal":"recomp","activity_level":"moderate","training_days_per_week":4})
today=datetime.date.today().isoformat()
post("/body",{"date":today,"weight_kg":72,"bodyfat_pct":16})
d=get("/meals"); print("[0] 空记录: items=",len(d["items"]),"target存在=",bool(d["target"]))
post("/meals/from-foods",{"date":today,"slot":"breakfast","items":[{"name":"燕麦片（干）","grams":60},{"name":"鸡蛋","grams":100}]})
d=get("/meals")
print("[1] 只记早餐: items=",len(d["items"]),"target存在=",bool(d["target"]),"meals_complete=",d["meals_complete"])
print("    total=",d["total"])
print("    target=",d["target"])
print("    => JS 条件 (hasAny && tgt) =", bool(d["items"]) and bool(d["target"]), " 应显示已摄入/建议 ✓")
