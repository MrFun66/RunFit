"""GRF Coach 端到端冒烟测试。

用法：python tools/e2e_test.py [base_url]
默认 http://127.0.0.1:7788
"""
from __future__ import annotations

import json
import random
import sys
import uuid
from datetime import date, timedelta

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:7788"

PASS = 0
FAIL = 0
FAILS: list[str] = []


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name} {extra}")
    else:
        FAIL += 1
        FAILS.append(name)
        print(f"  FAIL  {name} {extra}")


def section(title: str) -> None:
    print(f"\n[{title}]")


# 合成 TCX：3 段心率、配速，含步频扩展
def make_tcx() -> bytes:
    start = "2026-10-10T07:00:00.000Z"
    pts = []
    # 40 个采样点，每 15 秒一个
    for i in range(40):
        t = 15 * i
        mm = t // 60
        ss = t % 60
        hr = 130 + i * 1  # 心率漂移
        dist = 3.0 * t  # 约 3 m/s
        speed = 3.0 + (i % 5) * 0.05
        pts.append(
            f'<Trackpoint><Time>2026-10-10T07:{mm:02d}:{ss:02d}.000Z</Time>'
            f'<DistanceMeters>{dist:.1f}</DistanceMeters>'
            f'<Cadence>170</Cadence>'
            f'<Extensions><TPX xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2">'
            f'<Speed>{speed:.3f}</Speed><RunCadence>170</RunCadence>'
            f'</TPX></Extensions>'
            f'<HeartRateBpm><Value>{hr}</Value></HeartRateBpm></Trackpoint>'
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">'
        '<Activities><Activity Sport="Running">'
        f'<Id>{start}</Id>'
        f'<Lap StartTime="{start}"><TotalTimeSeconds>600</TotalTimeSeconds>'
        '<DistanceMeters>3600</DistanceMeters><Calories>320</Calories>'
        '<AverageHeartRateBpm><Value>150</Value></AverageHeartRateBpm>'
        '<MaximumHeartRateBpm><Value>165</Value></MaximumHeartRateBpm>'
        '<Intensity>Active</Intensity><TriggerMethod>Manual</TriggerMethod>'
        '<Track>' + "".join(pts) + '</Track></Lap>'
        '</Activity></Activities></TrainingCenterDatabase>'
    )
    return xml.encode("utf-8")


def main() -> None:
    c = httpx.Client(base_url=BASE, timeout=30.0)

    section("健康检查")
    r = c.get("/api/health")
    check("health", r.status_code == 200 and r.json().get("ok"), str(r.json()))
    llm_configured = r.json().get("llm_configured", False)

    section("认证（全新测试用户）")
    uname = f"e2e_{uuid.uuid4().hex[:8]}"
    pwd = "Test#Passw0rd!" + uuid.uuid4().hex[:6]
    r = c.post("/api/auth/register", json={"username": uname, "password": pwd})
    check("register", r.status_code == 200, r.text[:120])
    r = c.get("/api/auth/status")
    check("status-logged-in", r.status_code == 200 and r.json().get("logged_in"), str(r.json()))

    section("用户档案")
    profile = {
        "sex": "male",
        "birth_year": 1995,
        "height_cm": 176,
        "weight_kg": 74.5,
        "bodyfat_pct": 18.0,
        "goal": "recomp",
        "training_days_per_week": 4,
        "activity_level": "moderate",
        "hr_max": 190,
        "hr_rest": 58,
    }
    r = c.put("/api/profile", json=profile)
    check("profile-put", r.status_code == 200, r.text[:120])
    r = c.get("/api/profile")
    check("profile-get", r.status_code == 200 and r.json().get("weight_kg") == 74.5, r.text[:120])

    section("体测记录")
    today = date.today()
    for i, w in enumerate([75.2, 74.9, 74.5]):
        r = c.post(
            "/api/body",
            json={
                "date": (today - timedelta(days=14 - i * 7)).isoformat(),
                "weight_kg": w,
                "bodyfat_pct": 18.5 - i * 0.25,
            },
        )
        check(f"body-post-{i}", r.status_code == 200, r.text[:100])
    r = c.get("/api/body")
    check("body-get", r.status_code == 200 and len(r.json().get("items", [])) >= 3, r.text[:100])

    section("跑步数据上传与解析")
    tcx = make_tcx()
    files = {"file": ("e2e_run.tcx", tcx, "application/xml")}
    r = c.post("/api/runs/upload", files=files)
    check("run-upload", r.status_code == 200, r.text[:200])
    r = c.get("/api/runs")
    runs = r.json().get("items", [])
    check("run-list", len(runs) >= 1, f"count={len(runs)}")
    if runs:
        rid = runs[0]["id"]
        r = c.get(f"/api/runs/{rid}")
        check("run-detail", r.status_code == 200, r.text[:150])
        d = r.json()
        check("run-has-pace", d.get("avg_pace_s_per_km") is not None, str(d.get("avg_pace_s_per_km")))
        check("run-has-hr", d.get("avg_hr") is not None, str(d.get("avg_hr")))
        check("run-has-cadence", d.get("avg_cadence") is not None, str(d.get("avg_cadence")))
        check("run-has-splits", bool(d.get("splits")), f"n={len(d.get('splits') or [])}")
        hz = d.get("hr_zones") or []
        check("run-has-zones", len(hz) == 5, f"n={len(hz)}")
    r = c.get("/api/runs/stats")
    check("run-stats", r.status_code == 200, r.text[:150])

    section("训练模板（三分化）")
    r = c.get("/api/templates")
    tpls = r.json().get("items", [])
    check("templates", len(tpls) >= 3, f"count={len(tpls)} names={[t.get('name') for t in tpls]}")
    if tpls:
        t = tpls[0]
        tid = t["id"]
        items = t.get("items", [])
        check("template-items", len(items) > 0, f"n={len(items)}")
        weights = {it["exercise_id"]: 40.0 + i * 5 for i, it in enumerate(items)}
        rpes = {it["exercise_id"]: 8.0 for it in items}
        r = c.post(
            f"/api/templates/{tid}/log",
            json={"date": today.isoformat(), "weights": weights, "rpes": rpes, "duration_min": 60},
        )
        check("template-log", r.status_code == 200, r.text[:150])

    section("力量训练")
    r = c.get("/api/exercises")
    exs = r.json().get("items", [])
    check("exercises", len(exs) >= 10, f"count={len(exs)}")
    r = c.post(
        "/api/workouts",
        json={
            "date": today.isoformat(),
            "name": "推日",
            "focus": "push",
            "duration_min": 65,
            "sets": [
                {"exercise_id": exs[0]["id"], "weight_kg": 60, "reps": 8, "rpe": 8},
                {"exercise_id": exs[0]["id"], "weight_kg": 60, "reps": 8, "rpe": 8.5},
                {"exercise_id": exs[1]["id"], "weight_kg": 20, "reps": 12, "rpe": 7},
            ],
        },
    )
    check("workout-post", r.status_code == 200, r.text[:150])
    r = c.get("/api/workouts")
    check("workout-list", len(r.json().get("items", [])) >= 1, r.text[:100])
    r = c.get("/api/strength/stats")
    check("strength-stats", r.status_code == 200, r.text[:150])
    r = c.get("/api/strength/plan")
    check("strength-plan", r.status_code == 200, r.text[:150])

    section("营养")
    r = c.get("/api/nutrition/plan")
    check("nutrition-plan", r.status_code == 200, r.text[:150])
    if r.status_code == 200:
        n = r.json()
        check("nutrition-tdee", (n.get("tdee") or {}).get("tdee", 0) > 1500, str((n.get("tdee") or {}).get("tdee")))
    r = c.post(
        "/api/meals",
        json={
            "date": today.isoformat(),
            "slot": "lunch",
            "description": "鸡胸肉 150g + 米饭 200g + 西兰花",
            "kcal": 620,
            "protein_g": 45,
            "carb_g": 70,
            "fat_g": 12,
        },
    )
    check("meal-post", r.status_code == 200, r.text[:150])
    r = c.get("/api/meals")
    check("meal-list", len(r.json().get("items", [])) >= 1, r.text[:100])

    section("仪表盘")
    r = c.get("/api/dashboard")
    check("dashboard", r.status_code == 200, r.text[:150])
    if r.status_code == 200:
        d = r.json()
        check("dashboard-week", d["week"]["runs"] >= 1 and d["week"]["strength_sessions"] >= 1, str(d["week"]))

    section("AI 教练上下文")
    r = c.get("/api/coach/review")
    check("coach-review", r.status_code == 200, r.text[:120])
    ctx = r.json().get("context", "") if r.status_code == 200 else ""
    check("context-nonempty", len(ctx) > 200, f"len={len(ctx)}")
    check("context-has-run", "跑步数据" in ctx, "")
    check("context-has-strength", "力量训练数据" in ctx, "")
    check("context-has-nutrition", "营养数据" in ctx, "")

    if llm_configured:
        section("AI 教练流式对话（已配置 Key）")
        with c.stream(
            "POST", "/api/coach/stream", json={"message": "用一句话总结我这周的训练。", "module": "general"}
        ) as resp:
            check("coach-stream-status", resp.status_code == 200, str(resp.status_code))
            text = "".join(resp.iter_text())
        check("coach-stream-text", len(text) > 10, f"len={len(text)}")
    else:
        print("\n[跳过] AI 流式对话：未配置 GRF_LLM_API_KEY")

    section("前端静态资源")
    for path in ["/", "/assets/app.js", "/assets/style.css", "/manifest.json"]:
        r = c.get(path)
        check(f"static{path}", r.status_code == 200, f"{len(r.content)}B")

    print(f"\n=== 结果：PASS {PASS} / FAIL {FAIL} ===")
    if FAILS:
        print("失败项：", ", ".join(FAILS))
    c.close()
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()