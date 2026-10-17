# 域名接入说明（最终状态：已完成）

## 结论
**https://runfit.wenhh.top 已可正常访问。** 全部验证通过。

---

## 当初卡住的「填 IPv4」表单 —— 正确答案是：不要填

你在 Cloudflare 面板看到的「添加记录 → A 类型 → IPv4 地址」表单，
**不是隧道场景该用的东西**。隧道出口 IP 是动态的，没有固定 IPv4 可填。
隧道需要的是 CNAME → `<tunnel-id>.cfargotunnel.com`，
这条记录用一条命令自动生成：

`powershell
cloudflared tunnel route dns runfit runfit.wenhh.top
`

---

## 实际完成的操作链

| 步骤 | 内容 | 状态 |
|---|---|---|
| 1 | 删除旧的、错误的 Cloudflare zone | 你操作 |
| 2 | 重新 Add site → wenhh.top | 你操作 |
| 3 | Cloudflare 分配 NS：nita.ns.cloudflare.com / jobs.ns.cloudflare.com | 自动 |
| 4 | 西部数码（west.cn）把 NS 换成上面两条 | 你操作 |
| 5 | zone 状态 pending → ctive | 自动，约 10 分钟 |
| 6 | CNAME unfit.wenhh.top → 7ef935d8-....cfargotunnel.com | 已存在 |
| 7 | Universal SSL 证书签发 | 自动，约 10-15 分钟 |
| 8 | HTTPS 端到端验证 | ✅ 通过 |

---

## 最终基础设施

`
Cloudflare zone : 097542f34d22c0381ccdce10b79e3b8d   status = active
NS              : anita.ns.cloudflare.com / jobs.ns.cloudflare.com
A 记录          : 104.21.12.29 / 172.67.131.234   (Cloudflare 边缘)
CNAME           : runfit.wenhh.top -> 7ef935d8-55aa-40e7-a20c-8e7c55a99a98.cfargotunnel.com
隧道            : runfit (7ef935d8-55aa-40e7-a20c-8e7c55a99a98)
连接            : 2xlax01, 2xlax11
config.yml      : C:\Users\Administrator\.cloudflared\config.yml
本机后端        : http://127.0.0.1:7788
`

---

## 验证结果（6/6 PASS）

`
1. POST /api/auth/register  -> 200 {"ok":true,"username":"final_43404"}
2. POST /api/runs/upload    -> 200 {"imported":1,"skipped_duplicates":0,"errors":[]}
3. GET  /api/runs/stats     -> 200 480B   W41: 1跑 3.6km 10:00 配速2:46 心率149.5 负荷16.1
4. GET  /api/dashboard      -> 200 419B   llm_configured=true
5. GET  /                    -> 200 25697B
   GET  /manifest.json      -> 200 386B
   GET  /sw.js              -> 200 733B
6. GET  /api/health         -> 200 {"ok":true,"app":"GRF Coach","llm_configured":true}
`

---

## 日常启动方式

`powershell
# 窗口 1：后端
cd D:\GRF
python -m uvicorn app.main:app --host 0.0.0.0 --port 7788

# 窗口 2：隧道
cloudflared tunnel run runfit
`

访问：**https://runfit.wenhh.top**

---

## 常见问题

**Q：Cloudflare 面板显示"没有DNS记录"？**
A：那是因为面板里还没刷新，或者你看的是根域。unfit 子域的 CNAME 确实存在（API 已确认）。
根域 wenhh.top 本身没有 A 记录是正常的，我们只用子域。

**Q：证书过期怎么办？**
A：Cloudflare Universal SSL 自动续期，无需操作。

**Q：重启电脑后域名不通？**
A：隧道进程需要重新启动。把上面两个窗口的命令跑一遍即可。
需要开机自启的话，可以把 cloudflared tunnel run runfit 注册成 Windows 服务：
`powershell
cloudflared service install
`

**Q：改了 NS 会影响原来别的记录吗？**
A：会。NS 一换，解析完全由 Cloudflare 接管，西部数码那边的记录全部失效。
目前这个域名只跑 unfit 一个服务，没有影响。