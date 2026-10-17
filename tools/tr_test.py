import sys, io
sys.path.insert(0, r"D:\GRF")
from sqlalchemy import select
from app.db import SessionLocal
from app.models import User
from app import api as A
db = SessionLocal()
u = db.scalar(select(User).where(User.username == "WenHH"))
print("user:", u.id if u else None)
for g in ["day","week","month","year"]:
    r = A.strength_trend(grain=g, user=u, db=db)
    print(g, [b["label"] for b in r["buckets"]])
    print("   ", [(x["label"], x["color"], x["total"]) for x in r["series"]], "TOTAL", r["total_volume"])
