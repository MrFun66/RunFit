import sqlite3, io
db = sqlite3.connect(r"D:\GRF\grf.db")
cur = db.cursor()

UID = 19
print("=== BEFORE ===")
for t, cond in (("body_metrics", "user_id=? AND source='auto-sync'"),
                ("runs", "user_id=? AND source='auto-sync'"),
                ("health_samples", "user_id=?")):
    cur.execute(f"SELECT COUNT(*) FROM {t} WHERE {cond}", (UID,))
    print(t, cur.fetchone()[0])

cur.execute("DELETE FROM body_metrics WHERE user_id=? AND source='auto-sync'", (UID,))
print("deleted body_metrics:", cur.rowcount)
cur.execute("DELETE FROM runs WHERE user_id=? AND source='auto-sync'", (UID,))
print("deleted runs:", cur.rowcount)
cur.execute("DELETE FROM health_samples WHERE user_id=?", (UID,))
print("deleted health_samples:", cur.rowcount)
db.commit()

print("=== AFTER (user 19 only) ===")
cur.execute("SELECT date,weight_kg,bodyfat_pct,resting_hr,sleep_hours,source FROM body_metrics WHERE user_id=?", (UID,))
print("body:", cur.fetchall())
cur.execute("SELECT id,start_time,distance_m,name,source FROM runs WHERE user_id=?", (UID,))
print("runs:", cur.fetchall())
cur.execute("SELECT COUNT(*) FROM health_samples WHERE user_id=?", (UID,))
print("samples:", cur.fetchone()[0])
db.close()
