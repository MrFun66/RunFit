import sqlite3, json
c = sqlite3.connect(r"D:\GRF\grf.db")
c.row_factory = sqlite3.Row
cur = c.cursor()

print("=== users (id, username, has_token) ===")
for r in cur.execute("select id, username, sync_token is not null as tok from users order by id"):
    print(dict(r))

print("\n=== WenHH (id=19) body_metrics ===")
for r in cur.execute("select date, weight_kg, bodyfat_pct, resting_hr, sleep_hours, source from body_metrics where user_id=19 order by date desc"):
    print(dict(r))

print("\n=== WenHH health_samples ===")
for r in cur.execute("select date, metric, value, unit, source, created_at from health_samples where user_id=19 order by id"):
    print(dict(r))

print("\n=== WenHH runs ===")
for r in cur.execute("select name, start_time, distance_m, duration_s, source, created_at from runs where user_id=19 order by id"):
    print(dict(r))

print("\n=== test users count ===")
for r in cur.execute("select id, username from users where username like 'sync_%' or username like 'csv_%' or username like 'pub_%' or username like 'qtok_%' or username like 'ios%' or username like 'hm%' or username like 'cfg_%' or username like 'all_%' or username like 'big_%' or username like 'rawcsv_%' or username like 'txt_%' or username like 'fmt_%' or username like 'pubcsv_%' or username like 'pubf_%'"):
    print(dict(r))
c.close()
