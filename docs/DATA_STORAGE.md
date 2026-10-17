# 多用户数据存储说明

## 一、先回答你的问题：别人的数据存哪？

**现在：存在你这台机器的 D:\GRF\grf.db 里，但按账号严格隔离。**

- 物理位置：单个 SQLite 文件，约 160 KB
- 逻辑隔离：每张业务表都有 user_id 字段，所有查询强制 where user_id = 当前登录用户
- 实测验证：alice 写入的体重/体脂/身高/目标/饮食备注，bob 登录后**全部读到空值**

| 表 | 隔离方式 |
|---|---|
| runs 跑步 | user_id |
| workouts 力量训练 | user_id |
| workout_sets 组数 | 经 workout_id 间接 |
| meals 饮食 | user_id |
| body_metrics 身体数据 | user_id |
| coach_messages AI 对话 | user_id |
| nutrition_days | user_id |
| plan_weeks | user_id |
| workout_templates | user_id |
| exercises 动作库 | owner_id 为空 = 公共资源，共享 |
| template_items | 随模板归属 |

**结论：别人看不到你的数据，你也看不到别人的。但数据确实都在你电脑上。**

---

## 二、如果你不想存在自己机器上，三个方案

### 方案 A：保持现状（推荐先用这个）

- 成本：0
- 优点：零配置，现在就能用；数据完全自己掌控；无隐私外泄风险
- 缺点：电脑关机/断网 → 服务不可用；硬盘坏了 → 数据没了
- 适合：自己用 + 少量朋友（<10 人）

必做：定期备份 grf.db

    Copy-Item D:\GRF\grf.db "D:\GRF\backup\grf_$(Get-Date -Format yyyyMMdd).db"

---

### 方案 B：数据库搬到云（推荐给要给不少人用）

代码几乎不用改，只把 SQLite 换成云数据库。改动量：只改 app/config.py + app/db.py 的连接串。

| 选项 | 免费额度 | 说明 |
|---|---|---|
| Supabase (Postgres) | 500MB | 最推荐，有网页管理界面 |
| Neon (Postgres) | 0.5GB | 冷启动稍慢 |
| Turso (SQLite 兼容) | 9GB | 改动最小，语法几乎不变 |
| PlanetScale (MySQL) | 5GB | 需要改 SQL 语法 |

以 Turso 为例（改动最小，因为还是 SQLite）：

1. 注册 turso.tech，创建数据库
2. 拿到连接串和 token
3. .env 里加：

    GRF_DB_URL=libsql://grf-xxx.turso.io
    GRF_DB_TOKEN=eyJ...

4. app/db.py 改 create_engine 的 URL

- 成本：免费额度够 50~100 人
- 优点：数据在云端，你电脑关机别人也能用；自动备份
- 缺点：要注册账号、改配置

---

### 方案 C：整体搬到云服务器（推荐给当产品做）

- 成本：阿里云/腾讯云轻量服务器 ≈ 60~100 元/月（2核2G 够用）
- 优点：24 小时在线；域名直接绑服务器；可以装 HTTPS 证书
- 缺点：要花钱、要维护

步骤概要：

1. 买一台轻量应用服务器（Ubuntu 22.04）
2. 把 D:\GRF 整个目录传上去
3. 装 Python + 依赖
4. 用 systemd 守护后端
5. 服务器上跑 cloudflared tunnel run runfit（或 Nginx 反代）
6. 把 runfit.wenhh.top 的 DNS 指向新服务器

---

## 三、我的建议

- 3~10 个朋友 → 方案 A + 定期备份，别过度设计
- 20 人以上 / 想长期跑 → 方案 B（Turso），改动最小，免费额度够
- 要做成产品 → 方案 C

---

## 四、当前的实际风险（必须知道）

1. 单点故障：你电脑关机 / 断网 → 所有人用不了
2. 无自动备份：grf.db 损坏就全没了
3. 注册默认开放：GRF_ALLOW_REGISTER=1，任何人拿到网址都能注册

### 建议立刻做的三件事

1) 关掉公开注册（改成邀请制）

    .env 里改：GRF_ALLOW_REGISTER=0

2) 设一个定时备份（每天 3 点）

    schtasks /create /tn "GRF Backup" /tr "powershell -c Copy-Item D:\GRF\grf.db D:\GRF\backup\grf_$(Get-Date -Format yyyyMMdd).db" /sc daily /st 03:00

3) 定期检查磁盘：Get-PSDrive D | Select-Object Used,Free