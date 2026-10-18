import sqlite3
db = sqlite3.connect(r"D:\GRF\grf.db")
c = db.cursor()
def cols(t):
    return [r[1] for r in c.execute(f"PRAGMA table_info({t})").fetchall()]
for t in ("body_metrics","runs","health_samples"):
    print(t, cols(t))
print("=== body_metrics user19 ===")
for r in c.execute("SELECT * FROM body_metrics WHERE user_id=19 ORDER BY date").fetchall():
    print(r)
print("=== runs user19 ===")
for r in c.execute("SELECT * FROM runs WHERE user_id=19 ORDER BY id").fetchall():
    print(r)
print("=== health_samples user19 ===")
for r in c.execute("SELECT * FROM health_samples WHERE user_id=19 ORDER BY id").fetchall():
    print(r)
print("=== all users ===")
for r in c.execute("SELECT id,username FROM users").fetchall():
    print(r)
db.close()
