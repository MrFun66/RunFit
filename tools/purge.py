import sqlite3, shutil, datetime
db = r"D:\GRF\grf.db"
bak = db + ".bak_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(db, bak)
print("backup:", bak)

con = sqlite3.connect(db)
cur = con.cursor()

def cnt(sql):
    return cur.execute(sql).fetchone()[0]

print("\n=== BEFORE ===")
print("body_metrics total:", cnt("select count(*) from body_metrics"))
print("  auto-sync:", cnt("select count(*) from body_metrics where source='auto-sync'"))
print("runs total:", cnt("select count(*) from runs"))
print("  auto-sync:", cnt("select count(*) from runs where source='auto-sync'"))
print("health_samples total:", cnt("select count(*) from health_samples"))

cur.execute("delete from health_samples")
n1 = cur.rowcount
cur.execute("delete from body_metrics where source='auto-sync'")
n2 = cur.rowcount
cur.execute("delete from runs where source='auto-sync'")
n3 = cur.rowcount
cur.execute("delete from app_settings where key like 'last_sync_%'")
n4 = cur.rowcount
con.commit()

print("\n=== DELETED ===")
print("health_samples:", n1)
print("body_metrics(auto-sync):", n2)
print("runs(auto-sync):", n3)
print("last_sync settings:", n4)

print("\n=== AFTER ===")
print("body_metrics total:", cnt("select count(*) from body_metrics"))
print("runs total:", cnt("select count(*) from runs"))
print("health_samples total:", cnt("select count(*) from health_samples"))
con.close()
