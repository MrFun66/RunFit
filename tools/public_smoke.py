"""公网冒烟测试：注册 -> 上传 TCX -> 跑步分析 -> 仪表盘 -> AI 复盘。

用法: python tools/public_smoke.py [base_url]
默认读取 current_url.txt。
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else (ROOT / "current_url.txt").read_text(encoding="utf-8").strip()
    print(f"BASE = {base}")
    tcx = ROOT / "data" / "_t.tcx"
    assert tcx.exists(), f"缺少测试文件 {tcx}"

    results: list[tuple[str, bool, str]] = []

    def check(name: str, fn):
        try:
            val = fn()
            results.append((name, True, str(val)[:200]))
            print(f"  PASS {name}: {str(val)[:160]}")
            return val
        except Exception as e:  # noqa: BLE001
            results.append((name, False, f"{type(e).__name__}: {e}"))
            print(f"  FAIL {name}: {type(e).__name__}: {e}")
            return None

    with httpx.Client(base_url=base, timeout=120.0, follow_redirects=True) as c:
        # 0. health
        check("health", lambda: c.get("/api/health").raise_for_status().json())

        # 1. 注册（若已有用户则登录）
        username = f"smoke_{random.randint(10000, 99999)}"
        password = "Passw0rd!123"

        def _auth():
            r = c.post("/api/auth/register", json={"username": username, "password": password})
            if r.status_code == 403:
                r = c.post("/api/auth/login", json={"username": username, "password": password})
            r.raise_for_status()
            return r.json()

        check("register/login", _auth)
        check("auth-status", lambda: c.get("/api/auth/status").raise_for_status().json())

        # 2. 建档
        check(
            "profile",
            lambda: c.put(
                "/api/profile",
                json={
                    "sex": "male", "birth_year": 1995, "height_cm": 176,
                    "weight_kg": 74.5, "bodyfat_pct": 18, "goal": "recomp",
                },
            ).raise_for_status().json(),
        )

        # 3. 上传 TCX
        def _upload():
            with open(tcx, "rb") as f:
                r = c.post("/api/runs/upload", files={"file": (tcx.name, f, "application/xml")})
            r.raise_for_status()
            return r.json()

        up = check("runs/upload", _upload)

        # 4. 跑步列表 & 分析
        runs = check("runs-list", lambda: c.get("/api/runs").raise_for_status().json())
        run_id = None
        if up and isinstance(up, dict):
            run_id = up.get("id") or up.get("run_id")
        if not run_id and runs:
            items = runs.get("items") if isinstance(runs, dict) else runs
            if items:
                run_id = items[0].get("id")
        if run_id:
            check(f"runs/{run_id} 详情", lambda: c.get(f"/api/runs/{run_id}").raise_for_status().json())
        check("runs/stats", lambda: c.get("/api/runs/stats").raise_for_status().json())

        # 5. 力量
        check("exercises", lambda: len(c.get("/api/exercises").raise_for_status().json()))
        check("workouts", lambda: c.get("/api/workouts").raise_for_status().json())
        check("strength/stats", lambda: c.get("/api/strength/stats").raise_for_status().json())
        check("strength/plan", lambda: c.get("/api/strength/plan?days_per_week=4&goal=recomp").raise_for_status().json())

        # 6. 营养
        check("nutrition/plan", lambda: c.get("/api/nutrition/plan").raise_for_status().json())
        check(
            "meals/post",
            lambda: c.post(
                "/api/meals",
                json={"slot": "lunch", "description": "鸡胸肉 150g + 米饭 200g + 西兰花", "kcal": 650},
            ).raise_for_status().json(),
        )
        check("meals/list", lambda: c.get("/api/meals").raise_for_status().json())

        # 7. 仪表盘
        dash = check("dashboard", lambda: c.get("/api/dashboard").raise_for_status().json())

        # 8. AI 复盘（可能耗时）
        t0 = time.time()
        review = check("coach/review", lambda: c.get("/api/coach/review").raise_for_status().json())
        print(f"    review elapsed {time.time() - t0:.1f}s")

        # 9. AI 流式对话
        def _stream():
            chunks: list[str] = []
            with c.stream(
                "POST", "/api/coach/stream",
                json={"message": "用一句话点评我今天训练完成度。"},
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                        if payload in ("", "[DONE]"):
                            continue
                        try:
                            obj = json.loads(payload)
                        except json.JSONDecodeError:
                            chunks.append(payload)
                            continue
                        if isinstance(obj, dict):
                            chunks.append(obj.get("delta") or obj.get("text") or "")
                    elif not line.startswith("event:"):
                        chunks.append(line)
            text = "".join(chunks).strip()
            if not text:
                raise RuntimeError("流式响应为空")
            return {"chars": len(text), "head": text[:80]}

        check("coach/stream", _stream)

        # 10. 前端静态资源
        idx = check("index.html", lambda: (len(c.get("/").raise_for_status().text)))
        check("assets/app.js", lambda: len(c.get("/assets/app.js").raise_for_status().text))

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [(n, m) for n, ok, m in results if not ok]
    print(f"\n=== 公网冒烟: PASS {passed} / FAIL {len(failed)} ===")
    for n, m in failed:
        print(f"  - {n}: {m}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())