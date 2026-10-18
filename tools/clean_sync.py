import sqlite3, shutil, datetime, os

db = r"D:\GRF\grf.db"
if not os.path.exists(db):
    print("DB NOT FOUND"); raise SystemExit

bak = db + ".bak_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(db, bak)
print("backup:", bak)

con = sqlite3.connect(db)
cur = con.cursor()

def cnt(sql):
    try:
        return cur.execute(sql).fetchone()[0]
    except Exception as e:
        return "ERR:" + str(e)

print("\n=== BEFORE ===")
print("  body_metrics  :", cnt("select count(*) from body_metrics"))
print("  runs          :", cnt("select count(*) from runs"))
print("  health_samples:", cnt("select count(*) from health_samples"))

print("\n--- body_metrics rows ---")
try:
    for r in cur.execute("select id,user_id,date,weight_kg,bodyfat_pct,resting_hr,sleep_hours,source from body_metrics"):
        print("   ", r)
except Exception as e:
    print("  ERR", e)

print("\n--- runs rows ---")
try:
    for r in cur.execute("select id,user_id,name,distance_m,source from runs"):
        print("   ", r)
except Exception as e:
    print("  ERR", e)

print("\n--- health_samples rows ---")
try:
    for r in cur.execute("select id,user_id,date,metric,value,source from health_samples"):
        print("   ", r)
except Exception as e:
    print("  ERR", e)

print("\n--- app_settings keys ---")
try:
    for r in cur.execute("select key,value from app_settings"):
        print("   ", r)
except Exception as e:
    print("  ERR", e)

# ---- 清理测试数据 ----
for sql in (
    "delete from health_samples",
    "delete from body_metrics where source='auto-sync' or source='apple_health'",
    "delete from runs where source='auto-sync' or source='apple_health'",
    "delete from app_settings where key like 'last_sync_%'",
):
    try:
        cur.execute(sql)
    except Exception as e:
        print("SKIP:", sql, "->", e)
con.commit()

print("\n=== AFTER ===")
print("  body_metrics  :", cnt("select count(*) from body_metrics"))
print("  runs          :", cnt("select count(*) from runs"))
print("  health_samples:", cnt("select count(*) from health_samples"))
print("  last_sync keys:", cnt("select count(*) from app_settings where key like 'last_sync_%'"))
con.close()
