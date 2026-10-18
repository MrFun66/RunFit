import sqlite3, os
db = r"D:\GRF\grf.db"
con = sqlite3.connect(db)
cur = con.cursor()

print("=== users ===")
for r in cur.execute("select id, username from users order by id"):
    print(r)

print("\n=== body_metrics count by source ===")
for r in cur.execute("select source, count(*) from body_metrics group by source"):
    print(r)

print("\n=== runs count by source ===")
for r in cur.execute("select source, count(*) from runs group by source"):
    print(r)

print("\n=== health_samples count ===")
print(cur.execute("select count(*) from health_samples").fetchone())

print("\n=== health_samples rows ===")
for r in cur.execute("select id,user_id,date,metric,value,source from health_samples order by id desc limit 20"):
    print(r)

print("\n=== body_metrics rows (last 10) ===")
for r in cur.execute("select id,user_id,date,weight_kg,bodyfat_pct,source from body_metrics order by id desc limit 10"):
    print(r)

print("\n=== runs rows (last 10) ===")
for r in cur.execute("select id,user_id,start_time,distance_m,name,source from runs order by id desc limit 10"):
    print(r)

con.close()
