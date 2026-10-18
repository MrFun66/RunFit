import urllib.request as u, json, http.cookiejar, datetime, random
B="http://127.0.0.1:7788/api"
cj=http.cookiejar.CookieJar(); op=u.build_opener(u.HTTPCookieProcessor(cj))
def post(p,d=None):
    body=json.dumps(d).encode() if d is not None else b""
    return json.loads(op.open(u.Request(B+p,data=body,headers={"Content-Type":"application/json"}),timeout=30).read().decode())
def get(p): return json.loads(op.open(u.Request(B+p),timeout=30).read().decode())
un="nut3_%d"%random.randint(10000,99999)
post("/auth/register",{"username":un,"password":"pass1234"}); post("/auth/login",{"username":un,"password":"pass1234"})
post("/profile",{"sex":"male","birth_year":1998,"height_cm":178,"weight_kg":72,"bodyfat_pct":16,"goal":"recomp","activity_level":"moderate","training_days_per_week":4})
post("/body",{"date":datetime.date.today().isoformat(),"weight_kg":72,"bodyfat_pct":16})
p=get("/nutrition/plan")
print("plan keys:", list(p.keys()))
print("plan.plan keys:", list((p.get("plan") or {}).keys()))
print(json.dumps(p.get("plan"), ensure_ascii=False)[:600])
