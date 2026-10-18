import urllib.request as u, json, http.cookiejar, datetime, random
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def post(p,d=None):
    body=json.dumps(d).encode() if d is not None else b""
    return json.loads(op.open(u.Request(B+p,data=body,headers={"Content-Type":"application/json"}),timeout=30).read().decode())
def get(p): return json.loads(op.open(u.Request(B+p),timeout=30).read().decode())

un="v_%d"%random.randint(10000,99999)
post("/auth/register",{"username":un,"password":"pass1234"})
post("/auth/login",{"username":un,"password":"pass1234"})
post("/profile",{"sex":"male","birth_year":1998,"height_cm":178,"weight_kg":72,"bodyfat_pct":16,"goal":"recomp","activity_level":"moderate","training_days_per_week":4})
today=datetime.date.today().isoformat()
post("/body",{"date":today,"weight_kg":72,"bodyfat_pct":16})

print("[A] 未记录三餐 ->")
d=get("/meals"); print("   meals_complete=",d["meals_complete"],"| target=",d["target"],"| badge 应显示'还差早午餐'")

for slot,items in [("breakfast",[{"name":"燕麦片（干）","grams":60},{"name":"牛奶（全脂）","grams":250}]),
                   ("lunch",[{"name":"米饭","grams":200},{"name":"鸡胸肉（熟）","grams":150}]),
                   ("dinner",[{"name":"红薯","grams":200},{"name":"三文鱼","grams":130}])]:
    post("/meals/from-foods",{"date":today,"slot":slot,"items":items})

print("[B] 记录三餐后 ->")
d=get("/meals")
print("   meals_complete=",d["meals_complete"])
print("   slots_done=",d["slots_done"])
print("   total=",d["total"])
t=d["target"]
print("   target=",t)
print("   >> 前端会显示: 热量 %s / %s kcal, 蛋白 %s / %sg ..." % (round(d["total"]["kcal"]), t["kcal"] if t else "--", round(d["total"]["protein_g"]), t["protein_g"] if t else "--"))
print("[C] 食物库:")
f=get("/foods?q="+u.quote("鸡")); print("   鸡 ->",[x["name"] for x in f["items"]])
f=get("/foods?q="+u.quote("米饭")); print("   米饭 ->",[(x["name"],x["unit_g"]) for x in f["items"]])
