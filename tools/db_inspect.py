"""临时脚本：检查数据库用户与数据量。"""
import sqlite3
import sys

db = sys.argv[1] if len(sys.argv) > 1 else "grf.db"
c = sqlite3.connect(db)
c.row_factory = sqlite3.Row

print("=== tables ===")
for r in c.execute("select name from sqlite_master where type='table' order by name"):
    print(" ", r["name"])

print("=== users ===")
for r in c.execute("select id, username, created_at from users"):
    print(" ", dict(r))

print("=== counts ===")
for t in [
    "runs", "workouts", "workout_sets", "meals",
    "body_metrics", "coach_messages", "workout_templates", "template_items",
]:
    try:
        n = c.execute("select count(*) from " + t).fetchone()[0]
        print(" ", t, n)
    except Exception as e:  # noqa: BLE001
        print(" ", t, "ERR", e)