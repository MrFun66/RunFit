import sqlite3, glob, os
db = r"D:\GRF\grf.db"
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
cur = con.cursor()

for t in ("body_metrics","runs","health_samples"):
    n = cur.execute(f"select count(*) from {t}").fetchone()[0]
    print(f"\n=== {t}: {n} rows ===")
    for r in cur.execute(f"select * from {t} order by rowid desc limit 20"):
        print(dict(r))

print("\n=== workouts / meals / coach_messages (保留的真实数据) ===")
for t in ("workouts","meals","coach_messages"):
    n = cur.execute(f"select count(*) from {t}").fetchone()[0]
    print(t, n)
con.close()

print("\n=== backups ===")
for f in sorted(glob.glob(db + ".bak_*")):
    print(os.path.basename(f), os.path.getsize(f), os.path.getmtime(f))
