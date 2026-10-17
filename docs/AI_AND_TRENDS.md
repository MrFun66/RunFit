# AI 配置与数据趋势（本轮新增）

## 一、AI Key 改为「每人自带」

### 规则
| 用户 | 能否用 AI | 用谁的 Key |
|---|---|---|
| 站长（id 最小的用户） | 能 | 优先自己的；没配则用 .env 的 |
| 其他用户 | 必须先自己配 | 只有自己的，没有回退 |

### 实测证据
   普通用户（未配 key）:
     GET /api/settings/llm -> own=false, is_owner=false, configured=false, fallback=false
     POST /api/coach/chat   -> 400 "尚未配置 AI Key。请到「我的 → AI 设置」填入你自己的 API Key"

   配置假 key 后:
     own=true, configured=true, masked=sk-f***************3456

### 接口
| 方法 | 路径 | 作用 |
|---|---|---|
| GET | /api/settings/llm | 读配置（Key 脱敏返回） |
| PUT | /api/settings/llm | 保存 Key / base_url / model / vision_model |
| DELETE | /api/settings/llm | 清除 |
| POST | /api/settings/llm/test | 发一句话验证 Key 是否可用 |

### 新表 user_llm_configs
    user_id (PK), api_key, base_url, model, vision_model, updated_at

### 前端
「我的」页面新增「AI 设置」卡片：
- 状态徽标：已配置 / 使用站长默认 / 未配置
- API Key 输入框（password 类型，已配置时显示 sk-t****cdef 脱敏，留空表示不改）
- 接口地址、文本模型、视觉模型
- 保存 / 测试 / 清除 三个按钮

---

## 二、身体数据趋势图

### 接口
    GET /api/body/trends?days=30|90|180|365

返回结构：

    {
      "days": 180,
      "available": ["weight_kg", "bodyfat_pct", "resting_hr"],
      "metrics": {
        "weight_kg": {
          "label": "体重", "unit": "kg",
          "series": [{"date": "2026-06-01", "value": 78.0}, ...],
          "count": 5, "first": 78.0, "last": 74.9,
          "min": 74.9, "max": 78.0, "avg": 76.46, "delta": -3.1
        },
        ...
      }
    }

支持的 10 个指标：体重、体脂率、肌肉量、腰围、臀围、胸围、臂围、腿围、静息心率、睡眠。
**只有实际有数据的指标才会出现在 available 里**，前端下拉框据此动态生成。

### 前端
「我的」页面新增「数据趋势」卡片：
- 时间范围下拉：30 天 / 90 天 / 180 天 / 1 年
- 指标下拉：按 available 动态生成
- Chart.js 折线图（渐变填充、数据点多时自动隐藏圆点）
- 下方四宫格：最新 / 变化 / 最低 / 最高，变化为负显示绿色
- 底部：共 N 条记录 · 均值 X

### 实测（5 个时间点）
    weight_kg    : 5 点, 首=78.0 末=74.9 变化=-3.1 均=76.46 区间[74.9, 78.0]
    bodyfat_pct  : 5 点, 首=20.5 末=18.2 变化=-2.3 均=19.4  区间[18.2, 20.5]
    resting_hr   : 5 点, 首=62.0 末=57.0 变化=-5.0 均=59.2  区间[57.0, 62.0]

---

## 三、缓存问题已修

之前公网 `app.js` 一直返回旧版本（47657），根因是 Cloudflare 缓存。

修法：
1. `index.html` 里的引用改为 `/assets/app.js?v=yyyyMMddHHmm`，每次改动换版本号
2. 后端给 `/` 和 `/assets/*` 加 `Cache-Control: no-cache, must-revalidate`
3. `main.py` 里用自定义 `NoCacheStatic` 覆盖 StaticFiles

验证：公网 `app.js?v=202610172111` -> 200, 63459 bytes，含 loadTrends / loadAiConfig / renderTrend。

---

## 四、验证清单

| 检查项 | 结果 |
|---|---|
| 3 个新路由挂载 | GET/PUT/DELETE /api/settings/llm, POST /test, GET /api/body/trends |
| user_llm_configs 表 | 已建，6 字段 |
| 普通用户无 key 被拦 | 400，提示去「我的 → AI 设置」 |
| 普通用户配 key 后 | own=true, configured=true, 脱敏正常 |
| 趋势接口 | 3 指标 × 5 点，统计正确 |
| 前端 15 个 DOM 元素 | 全部存在 |
| 括号配平 | 434 / 434 |
| 公网静态资源 | index 38701 / app.js 63459，与本地一致 |