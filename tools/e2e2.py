import urllib.request as u, json, http.cookiejar, datetime, random
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def post(p,d=None):
    body=json.dumps(d).encode() if d is not None else b""
    return json.loads(op.open(u.Request(B+p,data=body,headers={"Content-Type":"application/json"}),timeout=30).read().decode())
def get(p): return json.loads(op.open(u.Request(B+p),timeout=30).read().decode())

un="nut2_%d"%random.randint(10000,99999)
post("/auth/register",{"username":un,"password":"pass1234"})
post("/auth/login",{"username":un,"password":"pass1234"})
post("/profile",{"sex":"male","birth_year":1998,"height_cm":178,"weight_kg":72,"bodyfat_pct":16,"goal":"recomp","activity_level":"moderate","training_days_per_week":4})
today=datetime.date.today().isoformat()
print("[body]", post("/body",{"date":today,"weight_kg":72,"bodyfat_pct":16}))
print("[plan]", get("/nutrition/plan").get("complete"))
for slot,items in [("breakfast",[{"name":"燕麦片（干）","grams":60},{"name":"牛奶（全脂）","grams":250}]),
                   ("lunch",[{"name":"米饭","grams":200},{"name":"鸡胸肉（熟）","grams":150}]),
                   ("dinner",[{"name":"红薯","grams":200},{"name":"三文鱼","grams":130}])]:
    post("/meals/from-foods",{"date":today,"slot":slot,"items":items})
d=get("/meals")
print("complete=",d["meals_complete"])
print("total=",d["total"])
print("target=",d["target"])
