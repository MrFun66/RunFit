import base64, io, json, sys, uuid
import httpx
from PIL import Image, ImageDraw

BASE = "http://127.0.0.1:7788"
c = httpx.Client(base_url=BASE, timeout=180.0)
print("health:", c.get("/api/health").json())

u = f"llm_{uuid.uuid4().hex[:8]}"
r = c.post("/api/auth/register", json={"username": u, "password": "Test#Passw0rd!" + uuid.uuid4().hex[:6]})
print("register:", r.status_code)
c.put("/api/profile", json={"sex":"male","birth_year":1995,"height_cm":176,"weight_kg":74.5,
                            "bodyfat_pct":18.0,"goal":"recomp","training_days_per_week":4,
                            "activity_level":"moderate","hr_max":190,"hr_rest":58})

print("\n--- 1. 对话 ---")
r = c.post("/api/coach/chat", json={"message":"用一句话说明你能帮我做什么。","module":"general"})
print("status:", r.status_code)
print(r.text[:600])

print("\n--- 2. 流式 ---")
with c.stream("POST","/api/coach/stream", json={"message":"这周跑两次怎么安排？","module":"run"}) as resp:
    print("status:", resp.status_code)
    txt = "".join(resp.iter_text())
print("len:", len(txt)); print(txt[:300])

print("\n--- 3. 识图 ---")
img = Image.new("RGB",(640,480),(245,240,230)); d=ImageDraw.Draw(img)
d.ellipse((60,40,580,440), fill=(255,255,255), outline=(210,210,210), width=4)
d.ellipse((110,250,300,400), fill=(250,250,245))
d.rounded_rectangle((330,260,520,380), radius=24, fill=(196,150,96))
for cx,cy in [(200,170),(250,150),(170,210)]:
    d.ellipse((cx-40,cy-35,cx+40,cy+35), fill=(76,145,65))
buf=io.BytesIO(); img.save(buf,format="JPEG",quality=88)
r = c.post("/api/meals/photo", files={"file":("meal.jpg",buf.getvalue(),"image/jpeg")})
print("status:", r.status_code)
print(r.text[:900])
