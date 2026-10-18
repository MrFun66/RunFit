import urllib.request as u, json, http.cookiejar, datetime, random
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def req(method,p,d=None):
    body=json.dumps(d).encode() if d is not None else None
    r=u.Request(B+p,data=body,method=method,headers={"Content-Type":"application/json"})
    return json.loads(op.open(r,timeout=30).read().decode())
def get(p): return req("GET",p)

un="v_%d"%random.randint(10000,99999)
req("POST","/auth/register",{"username":un,"password":"pass1234"})
req("POST","/auth/login",{"username":un,"password":"pass1234"})
req("PUT","/profile",{"sex":"male","birth_year":1998,"height_cm":178,"weight_kg":72,"bodyfat_pct":16,"goal":"recomp","activity_level":"moderate","training_days_per_week":4})
today=datetime.date.today().isoformat()
req("POST","/body",{"date":today,"weight_kg":72,"bodyfat_pct":16})

print("[A] 未记录三餐:")
d=get("/meals"); print("   meals_complete=",d["meals_complete"],"| target=",d["target"],"| slots_done=",d["slots_done"])

for slot,items in [("breakfast",[{"name":"燕麦片（干）","grams":60},{"name":"牛奶（全脂）","grams":250}]),
                   ("lunch",[{"name":"米饭","grams":200},{"name":"鸡胸肉（熟）","grams":150}]),
                   ("dinner",[{"name":"红薯","grams":200},{"name":"三文鱼","grams":130}])]:
    req("POST","/meals/from-foods",{"date":today,"slot":slot,"items":items})

print("[B] 记录三餐后:")
d=get("/meals"); t=d["target"]; tot=d["total"]
print("   meals_complete=",d["meals_complete"],"slots_done=",d["slots_done"])
print("   total=",tot)
print("   target=",t)
if t:
    print("   >> 界面显示: 热量 %s/%s kcal | 蛋白 %s/%sg | 碳水 %s/%sg | 脂肪 %s/%sg (%s)" % (
        round(tot["kcal"]), t["kcal"], round(tot["protein_g"]), t["protein_g"],
        round(tot["carb_g"]), t["carb_g"], round(tot["fat_g"]), t["fat_g"], t["day_type"]))
print("[C] 食物库搜索:")
for q in ["鸡","米饭","三文"]:
    f=get("/foods?q="+u.quote(q)); print("   %s -> %s" % (q, [(x["name"],x["unit_g"]) for x in f["items"]][:4]))
