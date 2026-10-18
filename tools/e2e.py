import urllib.request as u, json, http.cookiejar, datetime, random
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar()
op=u.build_opener(u.HTTPCookieProcessor(cj))
def post(p,d=None,fmt="json"):
    body=json.dumps(d).encode() if d is not None else b""
    r=u.Request(B+p,data=body,headers={"Content-Type":"application/json"})
    return json.loads(op.open(r,timeout=30).read().decode())
def get(p):
    return json.loads(op.open(u.Request(B+p),timeout=30).read().decode())

un="nut_%d"%random.randint(10000,99999)
post("/auth/register",{"username":un,"password":"pass1234"})
post("/auth/login",{"username":un,"password":"pass1234"})
post("/profile",{"sex":"male","birth_year":1998,"height_cm":178,"weight_kg":72,"goal":"recomp","activity_level":"moderate","training_days_per_week":4})

print("[1] meals empty:")
d=get("/meals")
print("   meals_complete=",d.get("meals_complete")," target=",d.get("target")," slots_done=",d.get("slots_done"))

print("[2] foods search:")
f=get("/foods?q=")
print("   count=",f.get("count")," first=",f["items"][0]["name"] if f.get("items") else None)
g=get("/foods?q="+u.quote("鸡胸"))
print("   search 鸡胸 ->", [x["name"] for x in g.get("items",[])][:5])

print("[3] add 3 meals from foods:")
today=datetime.date.today().isoformat()
plan=[("breakfast",[{"name":"燕麦片（干）","grams":60},{"name":"牛奶（全脂）","grams":250},{"name":"鸡蛋","grams":100}]),
      ("lunch",[{"name":"米饭","grams":200},{"name":"鸡胸肉（熟）","grams":150},{"name":"西蓝花","grams":200}]),
      ("dinner",[{"name":"红薯","grams":200},{"name":"三文鱼","grams":130},{"name":"菠菜","grams":150}])]
for slot,items in plan:
    r=post("/meals/from-foods",{"date":today,"slot":slot,"items":items})
    print("   ",slot,r)

print("[4] meals after:")
d=get("/meals")
print("   meals_complete=",d.get("meals_complete"))
print("   total=",d.get("total"))
print("   target=",d.get("target"))
print("   slots_done=",d.get("slots_done"))
print("   items=",len(d.get("items",[])))
