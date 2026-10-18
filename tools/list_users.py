import sqlite3
db = r"D:\GRF\grf.db"
con = sqlite3.connect(db)
c = con.cursor()

tables = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
print("tables:", tables)

print("\n=== all users ===")
for r in c.execute("select id, username, created_at from users order by id"):
    print(r)

for t in ("body_metrics","runs","health_samples","meals","workouts","coach_messages","app_settings"):
    if t not in tables:
        continue
    print("\n--- %s ---" % t)
    try:
        for r in c.execute("select user_id, count(*) from %s group by user_id order by user_id" % t):
            print(r)
    except Exception as e:
        print("  err", e)

print("\n=== distinct sources ===")
for t in ("body_metrics","runs","health_samples"):
    if t in tables:
        try:
            print(t, list(c.execute("select source, count(*) from %s group by source" % t)))
        except Exception as e:
            print(t, "err", e)
con.close()
