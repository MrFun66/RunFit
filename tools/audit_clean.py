import sqlite3, json
c = sqlite3.connect(r"D:\GRF\grf.db")
c.row_factory = sqlite3.Row

print("=== users ===")
for r in c.execute("select id, username, (sync_token is not null) tok from users order by id"):
    print(dict(r))

print("\n=== 测试账号残留检查 ===")
pat = ("sync_","ios_","ios2_","cfg_","all_","csv_","big_","pub_","pubcsv_","pubf_","txt_","qtok_","hm2_","fmt_","rawcsv_","test_","hm_","p43_","e2e")
rows = c.execute("select id, username from users").fetchall()
leftovers = [dict(r) for r in rows if any(r["username"].startswith(p) for p in pat)]
print("leftover test users:", leftovers if leftovers else "无")

print("\n=== 各表总行数 ===")
for t in ("users","body_metrics","runs","health_samples","meals","workouts","workout_sets","app_settings"):
    try:
        n = c.execute(f"select count(*) from {t}").fetchone()[0]
        print(f"  {t:18s} {n}")
    except Exception as e:
        print(f"  {t:18s} ERR {e}")

print("\n=== WenHH(id=19) 三张表 ===")
for t in ("body_metrics","runs","health_samples"):
    n = c.execute(f"select count(*) from {t} where user_id=19").fetchone()[0]
    print(f"  {t:18s} {n}")

print("\n=== last_sync 设置项 ===")
for r in c.execute("select key, value from app_settings where key like 'last_sync%'"):
    print(" ", r["key"], "=", r["value"])
c.close()
