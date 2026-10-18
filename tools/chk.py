import sqlite3
con=sqlite3.connect(r"D:\GRF\grf.db"); cur=con.cursor()
uid=19
print("=== body_metrics ===")
for r in cur.execute("select id,date,weight_kg,bodyfat_pct,resting_hr,sleep_hours,source from body_metrics where user_id=? order by id desc limit 5",(uid,)):
    print(" ", r)
print("=== health_samples (按指标统计) ===")
for r in cur.execute("select metric,count(*),min(date),max(date) from health_samples where user_id=? group by metric order by 2 desc limit 20",(uid,)):
    print(" ", r)
print("=== health_samples 最近 8 条 ===")
for r in cur.execute("select id,date,metric,value,unit,source,created_at from health_samples where user_id=? order by id desc limit 8",(uid,)):
    print(" ", r)
print("=== runs ===")
for r in cur.execute("select id,name,start_time,distance_m,duration_s,source from runs where user_id=? order by id desc limit 5",(uid,)):
    print(" ", r)
print("=== last_sync ===")
for r in cur.execute("select key,value from app_settings where key like 'last_sync%'"):
    print(" ", r)
con.close()
