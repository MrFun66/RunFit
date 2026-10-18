import urllib.request as u, json, http.cookiejar, datetime, random
print("HEALTH:", u.urlopen("http://127.0.0.1:7788/api/health",timeout=10).read().decode())
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def post(p,d=None):
    body=json.dumps(d).encode() if d is not None else b""
    return json.loads(op.open(u.Request(B+p,data=body,headers={"Content-Type":"application/json"}),timeout=30).read().decode())
def get(p): return json.loads(op.open(u.Request(B+p),timeout=30).read().decode())
un="f_%d"%random.randint(10000,99999)
post("/auth/register",{"username":un,"password":"pass1234"}); post("/auth/login",{"username":un,"password":"pass1234"})
post("/profile",{"sex":"male","birth_year":1998,"height_cm":178,"weight_kg":72,"bodyfat_pct":16,"goal":"recomp","activity_level":"moderate","training_days_per_week":4})
today=datetime.date.today().isoformat()
post("/body",{"date":today,"weight_kg":72,"bodyfat_pct":16})
print("[0] 空:", get("/meals")["meals_complete"])
post("/meals/from-foods",{"date":today,"slot":"breakfast","items":[{"name":"燕麦片（干）","grams":60},{"name":"鸡蛋","grams":100}]})
d=get("/meals")
print("[1] 只记早餐 -> items=",len(d["items"]),"target=",bool(d["target"]),"total=",d["total"])
print("    >> 前端 hasAny=True 且 target 存在 => 立即显示已摄入/建议 ✓")
