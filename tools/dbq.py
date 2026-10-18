import sqlite3
c=sqlite3.connect(r"D:\GRF\grf.db")
c.row_factory=sqlite3.Row
print("=== 最近 health_samples ===")
for r in c.execute("SELECT user_id,date,metric,value,unit,created_at FROM health_samples ORDER BY id DESC LIMIT 15"):
    print(dict(r))
print()
print("=== 最近 body_metrics ===")
for r in c.execute("SELECT user_id,date,weight_kg,bodyfat_pct,sleep_hours,resting_hr,source FROM body_metrics ORDER BY id DESC LIMIT 8"):
    print(dict(r))
print()
print("=== 最近 runs ===")
for r in c.execute("SELECT user_id,start_time,name,distance_m,duration_s,source FROM runs ORDER BY id DESC LIMIT 5"):
    print(dict(r))
print()
print("=== 各表计数 ===")
for t in ("health_samples","body_metrics","runs"):
    print(t, c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
