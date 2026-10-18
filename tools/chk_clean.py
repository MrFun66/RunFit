import sqlite3
db = r"D:\GRF\grf.db"
con = sqlite3.connect(db)
cur = con.cursor()

print("=== all users ===")
for r in cur.execute("select id, username, length(sync_token) from users order by id"):
    print(r)

print("\n=== per-user counts ===")
for uid, name in cur.execute("select id, username from users order by id").fetchall():
    bm = cur.execute("select count(*) from body_metrics where user_id=?", (uid,)).fetchone()[0]
    rn = cur.execute("select count(*) from runs where user_id=?", (uid,)).fetchone()[0]
    hs = cur.execute("select count(*) from health_samples where user_id=?", (uid,)).fetchone()[0]
    wk = cur.execute("select count(*) from workouts where user_id=?", (uid,)).fetchone()[0]
    ml = cur.execute("select count(*) from meals where user_id=?", (uid,)).fetchone()[0]
    if bm or rn or hs or wk or ml:
        print(f"  {uid:>3} {name:<28} body={bm} runs={rn} samples={hs} workouts={wk} meals={ml}")

print("\n=== last_sync settings ===")
try:
    for r in cur.execute("select key, value from app_settings where key like 'last_sync%'"):
        print(r)
except Exception as e:
    print("err", e)
con.close()
