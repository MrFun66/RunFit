import sqlite3
con = sqlite3.connect(r"D:\GRF\grf.db")
cur = con.cursor()

tables = ["body_metrics","runs","health_samples","meals","workouts","workout_sets","coach_messages"]
print("=== row counts ===")
for t in tables:
    try:
        n = cur.execute(f"select count(*) from {t}").fetchone()[0]
        print(f"{t:16s} {n}")
    except Exception as e:
        print(f"{t:16s} ERR {e}")

print("\n=== all body_metrics ===")
for r in cur.execute("select user_id,date,weight_kg,bodyfat_pct,resting_hr,sleep_hours,source from body_metrics order by user_id,date"):
    print(r)

print("\n=== all runs ===")
for r in cur.execute("select user_id,name,start_time,distance_m,duration_s,source from runs order by user_id"):
    print(r)

print("\n=== all health_samples ===")
for r in cur.execute("select user_id,date,metric,value,source from health_samples order by user_id"):
    print(r)

print("\n=== last_sync settings ===")
try:
    for r in cur.execute("select key,value from app_settings where key like 'last_sync%'"):
        print(r)
except Exception as e:
    print("ERR", e)
con.close()
