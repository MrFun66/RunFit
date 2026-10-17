import json, sys, uuid
import httpx

BASE = "http://127.0.0.1:7788"
c = httpx.Client(base_url=BASE, timeout=60.0)
ok = True

def check(name, cond, detail=""):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + name + ("  " + str(detail)[:150] if detail else ""))
    if not cond: ok = False

u = f"plan_{uuid.uuid4().hex[:8]}"
r = c.post("/api/auth/register", json={"username": u, "password": "Test#Passw0rd!" + uuid.uuid4().hex[:6]})
check("register", r.status_code == 200, r.text[:80])

print("\n[1] 读取动作库")
exs = c.get("/api/exercises").json()["items"]
check("exercises", len(exs) >= 40, f"count={len(exs)}")
by_name = {e["name"]: e for e in exs}
print("   可选动作:", ", ".join(list(by_name)[:6]), "...")

print("\n[2] 新建自定义计划")
payload = {
    "name": "我的上肢日",
    "focus": "upper",
    "note": "自建测试",
    "items": [
        {"exercise_id": exs[0]["id"], "sets": 4, "reps": "6-8", "rest_s": 120},
        {"exercise_id": exs[1]["id"], "sets": 3, "reps": "10-12", "rest_s": 90},
    ],
}
r = c.post("/api/templates", json=payload)
check("create", r.status_code == 200, r.text[:100])
new_id = r.json().get("id")

print("\n[3] 列表应包含新计划")
tpls = c.get("/api/templates").json()["items"]
mine = [t for t in tpls if t["name"] == "我的上肢日"]
check("list-has-mine", len(mine) == 1, f"total={len(tpls)}")
check("mine-items", len(mine[0]["items"]) == 2, f"n={len(mine[0]['items'])}")

print("\n[4] 编辑自定义计划：改名字+增删动作")
payload2 = {
    "name": "上肢日 v2",
    "focus": "upper",
    "note": "改过",
    "items": [
        {"exercise_id": exs[1]["id"], "sets": 5, "reps": "5", "rest_s": 180},
        {"exercise_id": exs[2]["id"], "sets": 3, "reps": "12-15", "rest_s": 60},
        {"exercise_id": exs[3]["id"], "sets": 3, "reps": "15", "rest_s": 60},
    ],
}
r = c.put(f"/api/templates/{new_id}", json=payload2)
check("update", r.status_code == 200, r.text[:100])
t = c.get(f"/api/templates/{new_id}").json()
check("update-name", t["name"] == "上肢日 v2", t["name"])
check("update-count", len(t["items"]) == 3, f"n={len(t['items'])}")

print("\n[5] 编辑内置模板（应自动克隆）")
builtin = [x for x in tpls if x.get("is_builtin")][0]
print("   内置模板:", builtin["name"], "id=", builtin["id"])
clone_payload = {
    "name": builtin["name"] + "（我的）",
    "focus": builtin["focus"],
    "note": None,
    "items": [{"exercise_id": exs[5]["id"], "sets": 4, "reps": "8", "rest_s": 120}],
}
r = c.put(f"/api/templates/{builtin['id']}", json=clone_payload)
check("edit-builtin", r.status_code == 200, r.text[:120])
res = r.json()
check("cloned-flag", res.get("cloned") is True, str(res))

print("\n[6] 克隆后内置模板应保持不变")
builtin_after = c.get(f"/api/templates/{builtin['id']}").json()
check("builtin-intact", len(builtin_after["items"]) == len(builtin["items"]),
      f"before={len(builtin['items'])} after={len(builtin_after['items'])}")

print("\n[7] 复制接口")
r = c.post(f"/api/templates/{builtin['id']}/duplicate")
check("duplicate", r.status_code == 200, r.text[:100])

print("\n[8] 用新计划记录训练")
r = c.post(f"/api/templates/{new_id}/log", json={
    "date": "2026-10-17",
    "weights": {exs[1]["id"]: 60.0},
    "rpes": {exs[1]["id"]: 8.0},
    "duration_min": 55,
})
check("log", r.status_code == 200 and r.json().get("sets") == 11, r.text[:120])

print("\n[9] 删除自定义计划")
r = c.delete(f"/api/templates/{new_id}")
check("delete", r.status_code == 200, r.text[:80])
after = c.get("/api/templates").json()["items"]
check("deleted", all(x["id"] != new_id for x in after), f"remain={len(after)}")

print("\n[10] 内置模板不可删除")
r = c.delete(f"/api/templates/{builtin['id']}")
check("builtin-protected", r.status_code == 404, f"status={r.status_code}")

print("\n=== " + ("ALL PASS" if ok else "HAS FAILURE") + " ===")
sys.exit(0 if ok else 1)