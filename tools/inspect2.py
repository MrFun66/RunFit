import sqlite3, datetime, json
db = r"D:\GRF\grf.db"
con = sqlite3.connect(db); cur = con.cursor()

def cols(t):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]

print("body_metrics cols:", cols("body_metrics"))
print("runs cols:", cols("runs"))
print("health_samples cols:", cols("health_samples"))

print("\n--- counts per user ---")
for t in ("body_metrics","runs","health_samples"):
    print(t, list(cur.execute(f"select user_id, count(*) from {t} group by user_id")))

print("\n--- user 19 body_metrics ---")
for r in cur.execute("select * from body_metrics where user_id=19"):
    print(r)
print("\n--- user 19 runs ---")
for r in cur.execute("select * from runs where user_id=19"):
    print(r)
print("\n--- user 19 health_samples ---")
for r in cur.execute("select * from health_samples where user_id=19"):
    print(r)

print("\n--- app_settings last_sync ---")
for r in cur.execute("select key,value from app_settings where key like 'last_sync%'"):
    print(r)
con.close()
