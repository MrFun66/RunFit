import sqlite3, json
c = sqlite3.connect(r"D:\GRF\grf.db")
c.row_factory = sqlite3.Row
u = c.execute("select id,username from users where username='WenHH'").fetchone()
print("user:", dict(u) if u else None)
uid = u["id"] if u else 19
print("\n--- body_metrics last 5 ---")
for r in c.execute("select date,weight_kg,bodyfat_pct,resting_hr,sleep_hours,source from body_metrics where user_id=? order by date desc limit 5",(uid,)):
    print(dict(r))
print("\n--- runs last 5 ---")
for r in c.execute("select name,start_time,distance_m,duration_s,avg_hr,source from runs where user_id=? order by id desc limit 5",(uid,)):
    print(dict(r))
print("\n--- health_samples count & last 10 ---")
print("count:", c.execute("select count(*) from health_samples where user_id=?",(uid,)).fetchone()[0])
for r in c.execute("select date,metric,value,unit from health_samples where user_id=? order by id desc limit 10",(uid,)):
    print(dict(r))
print("\n--- distinct metrics ---")
for r in c.execute("select metric,count(*) n from health_samples where user_id=? group by metric order by n desc limit 30",(uid,)):
    print(dict(r))
