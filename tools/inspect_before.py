import sqlite3, shutil, datetime, os
db = r"D:\GRF\grf.db"
bak = db + ".bak_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(db, bak)
print("backup:", bak)

con = sqlite3.connect(db)
cur = con.cursor()

print("\n=== users ===")
for r in cur.execute("select id, username from users order by id"):
    print(r)

print("\n=== WenHH(19) body_metrics ===")
for r in cur.execute("select date,weight_kg,bodyfat_pct,resting_hr,sleep_hours,source from body_metrics where user_id=19"):
    print(r)
print("=== WenHH runs ===")
for r in cur.execute("select name,start_time,distance_m,duration_s,source from runs where user_id=19"):
    print(r)
print("=== WenHH health_samples ===")
for r in cur.execute("select date,metric,value,source from health_samples where user_id=19"):
    print(r)
con.close()
