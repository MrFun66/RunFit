# Passkey / WebAuthn 说明

## 一、先纠正一个误解（重要）

**Passkey 不改变数据存在哪。**

openGym 用 passkey，只是把"输密码"换成"指纹 / 面容 / 设备 PIN 解锁"。
它的数据仍然存在自己部署的那台机器上的 SQLite 里 —— 和我们现在完全一样。

所以：
- 加 passkey 后，登录更方便、更安全（抗钓鱼、无密码泄露风险）
- 但"别人的数据存哪"的答案不变：还是存在你这台机器的 grf.db 里，只是按 user_id 严格隔离

---

## 二、已实现的功能

### 后端（app/webauthn_auth.py）

| 路由 | 作用 |
|---|---|
| POST /api/auth/passkey/register/begin | 已登录用户开始绑定设备，返回 challenge |
| POST /api/auth/passkey/register/finish | 校验 attestation，把公钥存库 |
| POST /api/auth/passkey/login/begin | 开始免密登录（可不传用户名，走 discoverable credential） |
| POST /api/auth/passkey/login/finish | 校验签名，成功后下发会话 Cookie |
| GET  /api/auth/passkey/list | 列出当前用户的已绑设备 |
| DELETE /api/auth/passkey/{id} | 移除设备 |
| GET  /api/auth/passkey/available | 探测能力（返回当前 rp_id / origin） |

### 新表 webauthn_credentials

    id, user_id, credential_id, public_key, sign_count,
    transports, name, created_at, last_used_at

### 前端

- 登录页：新增「用指纹 / 面容登录（Passkey）」按钮
- 我的页：新增「生物识别登录」卡片，可绑定 / 查看 / 移除设备

---

## 三、安全设计要点

1. **challenge 一次性 + 5 分钟过期**
   存在进程内 dict，用完即删。复用会返回 400（已实测验证）。

2. **rp_id / origin 动态推导**
   - 本地访问 http://127.0.0.1:7788 → rp_id = 127.0.0.1
   - 公网访问 https://runfit.wenhh.top → rp_id = runfit.wenhh.top
   也可在 .env 里用 GRF_WEBAUTHN_RP_ID / GRF_WEBAUTHN_ORIGIN 固定。

3. **公钥只存服务端**
   浏览器只保存私钥（在安全芯片 / TPM / Secure Enclave 里），服务端拿不到。

4. **sign_count 递增检测**
   每次认证后更新，可发现凭证被克隆的迹象。

5. **删除设备 = 撤销访问**
   即使别人拿到了你的设备，你在"我的"页移除后，该设备立即失效。

---

## 四、怎么用

### 第一次绑定（需要先用密码登录）

1. 打开 https://runfit.wenhh.top
2. 用用户名 + 密码登录
3. 点底部「我的」
4. 找到「生物识别登录（Passkey）」
5. 点「+ 绑定此设备」
6. 手机/电脑弹出指纹或面容验证 → 确认

### 以后登录

1. 打开 https://runfit.wenhh.top
2. 点「用指纹 / 面容登录（Passkey）」
3. 验证 → 直接进

> 不填用户名也可以（discoverable credential），系统会让你选账号。

---

## 五、必要条件（不满足会失败）

| 条件 | 说明 |
|---|---|
| **HTTPS 或 localhost** | Passkey 只在安全上下文可用。runfit.wenhh.top 是 HTTPS ✅ |
| 浏览器支持 | Chrome 108+ / Safari 16+ / Edge 108+ / Firefox 119+ |
| 设备有生物识别或 PIN | 手机、带 Windows Hello 的电脑、Mac 的 Touch ID |

> 如果打开页面看不到按钮或提示"不支持"，通常是浏览器太旧，或者用的是 http:// 的 IP 地址。

---

## 六、和其他方案对比

| 方案 | 登录体验 | 数据存哪 | 改动量 |
|---|---|---|---|
| 现在（密码） | 要记密码 | 本机 SQLite | — |
| **Passkey（已实现）** | 指纹/面容一键 | 本机 SQLite（不变） | 已完成 |
| 数据库搬到云 | 同上 | 云端 Postgres/SQLite | 改连接串 |
| 整体上云服务器 | 同上 | 云服务器 | 迁移部署 |

**结论：passkey 解决"登录体验"，不解决"数据在哪"。这两件事要分开看。**

---

## 七、验证证据

- 7 个路由已挂载（openapi.json 可见）
- webauthn_credentials 表已建（9 个字段）
- register/begin 正常返回 challenge（86 字符）、rp_id 正确
- 伪造凭证 → 400 "id and raw_id were not equivalent"（正确拒绝）
- challenge 复用 → 400（正确拒绝）
- 公网 rp_id = runfit.wenhh.top，origin = https://runfit.wenhh.top
- 公网 app.js 54639 字节，含 passkeyRegister / passkeyLogin / loadPasskeys
- 静态资源已加 no-cache + 版本号，避免 CF 缓存旧文件