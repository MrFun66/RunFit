# RunFit

> 自托管的全方位教练：**力量训练日志 + 跑步数据深度分析 + 营养建议**，三合一，并接入 AI 给出可执行反馈。

一套跑在自己机器上的训练管理系统。数据不出本地，手机浏览器打开即用（可添加到主屏幕当 App）。

---

## 为什么做这个

市面上的训练 App 各管一摊：跑步的不管力量，记饮食的不看训练负荷，AI 助手又拿不到你的真实数据。
RunFit 把三份数据放在同一张表里，让「营养师 + 跑步分析师 + 力量教练」同时看到全貌，再让 AI 基于真实数据给建议——而不是泛泛而谈。

**核心主张：只依据数据说话。数据不足时明确告诉你缺什么，不编造。**

---

## 功能

### 力量训练
- **43 个动作库**，含主/次动肌肉映射，按推/拉/腿分类
- **三分化模板**（推日 / 拉日 / 腿日），一键生成当天训练记录，只需填重量和 RPE
- **肌肉容量热力图**：近 7 天各肌群组数 vs MEV/MAV/MRV 区间，直接告诉你哪块练少了、哪块过量
- **计划生成器**：按目标（减脂增肌/增肌/减脂）和每周训练天数，输出上下肢或推拉腿分化方案

### 跑步数据
支持从 Apple Watch 生态导入，解析器全部自己实现，不依赖第三方 SDK：

| 格式 | 来源 | 说明 |
|---|---|---|
| `.tcx` | WorkOutDoors / Garmin / Apple | 主力格式，含心率、步频、速度扩展 |
| `.gpx` | 通用 GPS 轨迹 | 自动从坐标算距离（Haversine） |
| `export.xml` | Apple 健康全量导出 | 两遍流式解析，几百 MB 也不吃内存 |
| `.csv` | WorkOutDoors / Strava 批量导出 | 批量导入历史 |

分析维度：
- 配速、平均/最大心率、步频、爬升、卡路里
- **心率区间分布**（Karvonen 五区，基于心率储备）
- **每公里分段**，含分段配速/心率/步频/爬升
- **训练负荷 TRIMP**（Banister）+ **ACWR**（急慢性负荷比），预警过度训练
- **有氧解耦**（前半程 vs 后半程 心率/配速比），看有氧耐力是否撑得住

### 营养
- **TDEE 计算**：BMR（Mifflin-St Jeor）+ 活动系数 + 跑步/力量训练额外消耗
- **宏量分配**：按目标给蛋白质/碳水/脂肪克数，区分训练日与休息日
- **拍照识餐**：拍一张饭菜照片，AI 视觉模型识别食物、估算克数与宏量，直接写入当日记录
- 体重趋势、体脂率、围度记录

### AI 教练
一个系统提示词里装三个人格（营养师 / 跑步分析师 / 力量教练），每次提问自动注入你的完整数据上下文：

```
用户档案 + 跑步数据 + 力量训练数据 + 营养数据
                    ↓
        DeepSeek (deepseek-flash)
                    ↓
   具体到数字和动作的建议（≤500 字）
```

- 支持流式输出（逐字显示）
- 支持多轮对话，历史落库
- 内置快捷提问：周复盘、下次训练建议、饮食调整

---

## 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| 后端 | FastAPI + SQLAlchemy 2.x | 类型友好，自带 OpenAPI 文档 |
| 数据库 | SQLite | 单用户场景零运维，文件即数据 |
| 前端 | 原生 JS + Tailwind CDN + Chart.js | 无构建步骤，改完刷新即生效 |
| 解析 | lxml（流式 iterparse） | Apple 导出文件动辄数百 MB |
| 认证 | bcrypt + 服务端 Session | 单用户强密码，防公网乱入 |
| AI | DeepSeek（OpenAI 兼容协议） | 国内直连，便宜，支持原生多模态识图 |
| 内网穿透 | cloudflared | 免费，无需备案 |

**依赖极少**：无 Node、无 Webpack、无 Docker 必需项。Python 3.11+ 即可。

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
```

编辑 `.env`，至少填一项：

```ini
GRF_LLM_API_KEY=sk-xxxxxxxx    # 不填则 AI 教练不可用，其他功能正常
```

> 没有 Key 也能用，只是「AI 教练」页面会提示未配置。

### 3. 启动

**Windows 一键（推荐）** —— 双击 `start.bat`，自动完成：清理旧进程 → 启动后端 → 起公网隧道 → 打印访问地址。

**手动启动**：

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 7788
```

打开 <http://127.0.0.1:7788>，首次访问注册账号（单用户模式，注册后自动关闭注册入口）。

---

## 公网访问

`start.bat` 会调用 cloudflared 生成临时地址（形如 `https://xxx.trycloudflare.com`），写入 `current_url.txt`。
手机浏览器打开该地址 → 分享 → 添加到主屏幕，体验接近原生 App。

**想要固定地址**，两条路：
1. **自有域名 + cloudflared 命名隧道**（免费，推荐）
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create runfit
   cloudflared tunnel route dns runfit runfit.yourdomain.com
   cloudflared tunnel run --url http://127.0.0.1:7788 runfit
   ```
2. 直接买一个便宜域名（`.top` / `.xyz` 首年通常 ¥10 以内），配合同上。

> 注意：`trycloudflare.com` 临时地址每次重启都会变。

---

## 数据从哪来

### 跑步
- **WorkOutDoors**：App 内导出 `.tcx`（推荐，数据最全）
- **Apple 健康**：iPhone 健康 App → 头像 → 导出所有健康数据 → 得到 `export.xml`（几百 MB，直接传，后端流式解析）

### 力量
网页填表：选模板 → 填每组重量和 RPE → 保存。也可自由添加动作。

### 饮食
拍照上传，或手动填描述 + 宏量。

---

## 项目结构

```
RunFit/
├── app/
│   ├── main.py            # 入口，静态文件挂载，启动时建表/播种
│   ├── config.py          # .env 读取
│   ├── db.py              # 引擎与会话
│   ├── models.py          # ORM 模型
│   ├── security.py        # bcrypt + session
│   ├── api.py             # 全部 REST 路由
│   ├── parsers.py         # TCX/GPX/Apple XML/CSV 解析（核心，673 行）
│   ├── analytics.py       # 心率区间、TRIMP、ACWR、解耦
│   ├── nutrition.py       # TDEE、宏量、周计划
│   ├── strength.py        # 肌肉容量、MEV/MAV/MRV、计划生成
│   ├── llm.py             # DeepSeek 客户端 + 系统提示词
│   ├── exercises_seed.py  # 43 个动作 + 肌肉映射
│   └── templates_seed.py  # 三分化模板
├── web/
│   ├── index.html         # 单页应用
│   ├── assets/app.js      # 前端逻辑
│   ├── assets/style.css
│   ├── manifest.json      # PWA
│   └── sw.js              # Service Worker
├── tools/
│   ├── e2e_test.py        # 端到端测试（41 项）
│   ├── verify_llm.py      # AI 连通性验证（对话+流式+识图）
│   └── make_test_tcx.py   # 生成合成 TCX
├── start.bat / start.ps1  # 一键启动
└── .env.example
```

---

## 测试

```bash
# 端到端（注册→档案→力量→跑步→营养→仪表盘→AI 上下文→静态资源）
python tools/e2e_test.py

# AI 专项（对话 + 流式 + 识图，需先配好 Key）
python tools/verify_llm.py
```

最近一次结果：**41 项全通过**。

---

## 几个实现上的取舍

**为什么自己写解析器，不用现成库？**
Apple 的 `export.xml` 动辄 500MB+，普通 DOM 解析直接爆内存。用 `lxml.iterparse` 流式两遍（第一遍扫 workout，第二遍扫关联的 HR/距离样本），内存占用稳定在几十 MB。TCX 的命名空间各家写法不同，统一抹掉 namespace 再按裸标签匹配，比维护 prefix map 表可靠。

**为什么用 SQLite 而不是 Postgres？**
单用户、单机、数据量小（几年训练数据也就几十 MB）。SQLite 零配置、单文件备份、随时拷走。真要多用户再迁，SQLAlchemy 换连接串即可。

**为什么前端不用框架？**
整个前端约 600 行 JS。引入 React/Vue 带来的构建链和依赖升级成本，远大于它省下的代码量。Tailwind 走 CDN，改样式不用重启。

**AI 上下文怎么控制长度？**
不是把原始数据全塞进去。跑步只给周汇总 + 最近几次的关键指标，力量只给肌肉容量与容量趋势，营养只给目标与实际差值。压缩后约 3KB，既能给出具体建议，又不浪费 token。

---

## 隐私

- 所有数据存在本地 `grf.db`
- `.env`、数据库、上传文件均在 `.gitignore` 中，不会进仓库
- 只有你主动点击「问教练」时，聚合后的数据摘要才会发给 DeepSeek

---

## License

MIT