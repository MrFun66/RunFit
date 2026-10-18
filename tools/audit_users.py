import sqlite3
db = sqlite3.connect(r"D:\GRF\grf.db")
c = db.cursor()
print("=== ALL USERS ===")
for r in c.execute("select id, username, created_at from users order by id"):
    print(r)
print("=== per-user counts ===")
for r in c.execute("""select u.id, u.username,
  (select count(*) from body_metrics b where b.user_id=u.id),
  (select count(*) from runs r where r.user_id=u.id),
  (select count(*) from health_samples h where h.user_id=u.id)
  from users u order by u.id"""):
    print(r)
db.close()
