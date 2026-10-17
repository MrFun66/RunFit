# RunFit / GRF Coach

自托管的「全方位教练」Web 应用：**力量训练日志 + 跑步数据分析 + 营养建议**，并用大模型给出可执行反馈。
单机可跑，手机浏览器添加到主屏幕后像 App 一样使用（PWA）。

---

## 主要功能

### 首页（今日概览）
- 本周跑量 / 力量训练次数 / 体重 / 体脂 四个关键指标
- 右上角 **+** 弹窗录入今日身体数据（体重、体脂、静息心率、睡眠）
- AI 教练面板：周报 / 训练计划 / 跑步分析 / 饮食分析四类报告
  - 先选标签再点「生成」，不会点一下就跑模型
  - 右上角实时显示 AI 配置状态；未配置时点一下直接告诉你去哪配

### 跑步
- 上传 WorkOutDoors / Apple Watch 导出的 TCX
- 配速、心率区间、步频、有氧解耦、训练负荷（TRIMP/ACWR）分析

### 力量训练
- **训练容量柱状图，可切换 日 / 周 / 月 / 年**
  - 日：横轴是肌群（胸/背/肩/手臂/腿/核心），不同颜色代表不同部位
  - 周：周一…周日；月：第一周…第四周；年：1月…12月
  - 按部位堆叠，图例带颜色块
  - 没数据时显示友好空态提示，不是一片白
- 今日记录卡片右上角「编辑」，直接覆盖重写当天记录（不会叠加）
- 只显示当天记录，避免界面杂乱

### 饮食与营养
- 按 **早餐 / 午餐 / 晚餐 / 加餐** 四个餐次分组展示
- **拍照或从相册选图识餐**：
  - 不再强制调用相机，可以直接选已有照片
  - 上传前在手机上先压缩到长边 1280px / JPEG 0.82，避免大图上传超时
  - 识别完可选择记到哪个餐次，一键确认入库
- 今日宏量目标与实际对比

### 我的 / 设置
- 个人基础资料、身体数据历史（从首页 + 录入）
- AI 设置：每个用户自己的 DeepSeek API Key / 模型 / 视觉模型
- 修改密码、Passkey（指纹 / 面容）绑定与管理
- 导入 Apple 健康 `export.xml`（体重、体脂、静息心率、睡眠）

### 体验细节
- 底部导航：首页 / 跑步 / 力量 / 饮食 / 我的（导航图标为跑步小人、哑铃、餐具）
- 下拉刷新
- 全站中文错误提示：不再出现 `Failed to fetch` / `A request is already pending` / `[object Object]` 这类看不懂的英文

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + Uvicorn |
| 数据库 | SQLite（`grf.db`，单文件，无需额外部署） |
| 前端 | 原生 HTML + Tailwind CSS + Chart.js（均本地托管，不走 CDN） |
| 认证 | Cookie Session + WebAuthn / Passkey |
| AI | DeepSeek（OpenAI 兼容协议），支持文本与多模态识图 |
| 公网 | Cloudflare Tunnel（无需公网 IP） |

> 重要：Chart.js 和 Tailwind 已改为本地文件（`web/assets/vendor/`）。
> 之前用 CDN 在国内网络下经常加载不出来，直接导致柱状图一片白。

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制环境变量模板
copy .env.example .env
# 然后编辑 .env，至少填一个可用的 GRF_LLM_API_KEY（也可以登录后在「我的→设置」里填）

# 3. 启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 7788
```

打开 <http://127.0.0.1:7788> 即可。

### 公网访问（选做）
```powershell
.\setup_tunnel.ps1     # 创建并启动 cloudflared 隧道
.\setup_domain.ps1     # 绑定自己的域名
```
细节见 `docs/DOMAIN.md`、`docs/域名接入-傻瓜版.md`。

---

## 目录结构

```
app/            后端（api / models / parsers / analytics / llm / security）
web/            前端静态页（index.html、assets/app.js、sw.js、vendor/）
docs/           部署与功能说明
tools/          辅助脚本（测试 / 修复）
data/           运行时数据（不入库）
logs/           日志（不入库）
```

---

## 常见问题

**Q：AI 报告点「生成」没反应？**
去「我的→设置→AI 设置」填入 API Key。首页 AI 教练卡片右上角会直接显示「未配置 API」。

**Q：拍照识餐提示识别失败？**
现在会先在手机上压缩照片，并且支持从相册选图。如果仍失败，界面会直接告诉你具体原因（Key 无效 / 超时 / 网络不通）。

**Q：力量柱状图为什么空的？**
两种可能：今天（或本周/月/年）确实没记录，会显示文字空态；或者浏览器缓存了旧版 `app.js`，强刷一次即可（版本号会自动更新）。

---

## 更新日志

详见 [CHANGELOG.md](./CHANGELOG.md)。

## 许可证

MIT，见 [LICENSE](./LICENSE)。
