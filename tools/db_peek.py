import sqlite3, datetime
con = sqlite3.connect(r"D:\GRF\grf.db")
con.row_factory = sqlite3.Row
c = con.cursor()

print("=== BEFORE (user 19 = WenHH) ===")
for q, lab in [
    ("select date,weight_kg,bodyfat_pct,resting_hr,sleep_hours,source,created_at from body_metrics where user_id=19 order by date", "body_metrics"),
    ("select name,distance_m,duration_s,source,start_time from runs where user_id=19", "runs"),
    ("select date,metric,value,source,created_at from health_samples where user_id=19", "health_samples"),
]:
    print("--", lab)
    for r in c.execute(q).fetchall():
        print("  ", dict(r))

print("=== all users ===")
for r in c.execute("select id,username from users order by id").fetchall():
    print("  ", r["id"], r["username"])
