# GRF「全方位教练」交付总结

生成时间：2026-10-17

## 一、目标达成情况

| 目标项 | 状态 | 证据 |
|---|---|---|
| 自托管 Web 应用（FastAPI + SQLite + 静态 SPA/PWA） | 已完成 | `app/main.py`、`app/api.py`（36 个 `/api` 路由）、`web/` |
| 力量训练日志与计划 | 已完成 | `/api/workouts`、`/api/strength/stats`、`/api/strength/plan`、`/api/templates*` |
| 跑步数据深度分析（TCX / export.xml 解析） | 已完成 | `/api/runs/upload`、`/api/runs/stats`（周汇总/总里程/ACWR）、`/api/runs` |
| 营养建议 | 已完成 | `/api/nutrition/plan`、`/api/meals`、`/api/meals/photo`（TDEE/宏量营养素） |
| AI 反馈 | 已完成 | `/api/coach/chat`、`/api/coach/stream`、`/api/coach/review`；`/api/health` → `llm_configured:true`（DeepSeek） |
| 内网穿透到公网可访问 | 已完成 | cloudflared quick tunnel → `http://127.0.0.1:7788` |
| 本地运行验证通过 | 已完成 | `logs/e2e_last.txt`：**PASS 43 / FAIL 0** |
| 公网运行验证通过 | 已完成 | `logs/public_smoke_last.txt`：**5/5 PASS** |

## 二、公网端到端验证（真实链路：公网 → tunnel → 7788 → FastAPI）

BASE: `https://arg-specializing-unnecessary-scene.trycloudflare.com`

```
1. POST /api/auth/register   -> {"ok":true,"username":"pub_261160"}                    PASS
2. POST /api/runs/upload     -> {"imported":1,"skipped_duplicates":0,"errors":[]}      PASS  (TCX)
3. GET  /api/runs/stats      -> 200, 438B (weeks / total_km 3.6 / acwr)                PASS
4. GET  /api/dashboard       -> 200 (week.runs=1, run_km=3.6, llm_configured=true)     PASS
5. GET  /api/runs            -> 200, 816B (items[0].id=12, 3600m / 600s)               PASS
```

覆盖链路：注册 → 会话 Cookie 保持 → TCX 文件上传解析 → 统计聚合 → 看板聚合 → 列表查询。

## 三、本地回归验证

`logs/e2e_last.txt`：**总计 PASS 43 / FAIL 0**。覆盖模板、力量统计/计划、营养计划/TDEE、餐食、
看板、教练点评 + 流式输出，以及静态资源（index 25330B / app.js 41393B / style.css 1296B / manifest.json 386B）。

## 四、运行方式

```powershell
cd D:\GRF
python -m uvicorn app.main:app --host 0.0.0.0 --port 7788
```

- 本机访问：http://127.0.0.1:7788
- 接口文档：http://127.0.0.1:7788/docs
- 临时公网地址记录在 `current_url.txt`

## 五、唯一剩余项：固定域名 wenhh.top（需用户操作）

当前 `wenhh.top` 的 NS 仍在新网（`ns1.myhostadmin.net` / `ns2.myhostadmin.net`），
Cloudflare 面板该 zone 显示"没有DNS记录"。Cloudflare 免费版**必须整域迁移 NS**，
不支持部分接管或 CNAME 接入，因此这一步无法由脚本自动完成，需要你在注册商处改 NS。

步骤：

1. Cloudflare → Add a site → 输入 `wenhh.top` → 选 Free 计划 → 记下分配到的两条 NS。
2. 登录新网域名控制台 → 修改 DNS 服务器 → 换成上面两条 NS。
3. 等待生效（通常几分钟到 24 小时），验证：
   ```powershell
   Resolve-DnsName wenhh.top -Type NS -Server 8.8.8.8
   ```
   返回 `*.ns.cloudflare.com` 即为生效。
4. 生效后执行（会打开浏览器授权一次）：
   ```powershell
   cd D:\GRF
   cloudflared tunnel login
   .\setup_tunnel.ps1
   ```
   脚本会自动创建 `runfit` 隧道、绑定 `runfit.wenhh.top` 的 DNS、写入 `~/.cloudflared/config.yml`
   并启动隧道。完成后固定地址为：**https://runfit.wenhh.top**

> 在此之前，临时 `trycloudflare.com` 地址随时可用，但 cloudflared 进程重启后会变化，
> 适合自己用，不适合长期对外分享。

## 六、相关文件

- `docs/DOMAIN.md` —— 域名接入的完整排障与步骤说明
- `setup_tunnel.ps1` —— 命名隧道一键脚本
- `tools/e2e_test.py` —— 本地端到端测试
- `logs/e2e_last.txt` / `logs/public_smoke_last.txt` —— 验证证据