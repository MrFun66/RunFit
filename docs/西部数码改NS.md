# 西部数码（west.cn）把 wenhh.top 的 NS 改成 Cloudflare

> 目标：让 wenhh.top 的 DNS 由 Cloudflare 托管，从而让 runfit.wenhh.top 生效。
> 不需要在 Cloudflare 面板里手动加任何 A 记录 / 不需要填 IPv4。

---

## 第 0 步：先拿到 Cloudflare 分给你的两条 NS

1. 登录 https://dash.cloudflare.com
2. 点进 wenhh.top 这个站点
3. 在 Overview（概述）页面，有一块 **Cloudflare Nameservers**，形如：
   aria.ns.cloudflare.com
   bob.ns.cloudflare.com
   （名字是随机分配的，以你看到的为准，不要照抄示例）
4. 把这两行完整复制下来

> 如果 Overview 显示 "Pending Nameserver Update" 黄色提示，
> 说明 Cloudflare 已经在等你改 NS —— 这正是你要做的。

---

## 第 1 步：登录西部数码

打开 https://www.west.cn/ ，用买域名时的账号登录。

---

## 第 2 步：进入域名管理

- 顶部「管理中心」→ 左侧「域名管理」→「我的域名」
- 或直接访问 https://www.west.cn/services/domain/

在列表里找到 **wenhh.top**，点右侧「管理」。

---

## 第 3 步：修改 DNS 服务器

在域名管理页找到下面任一入口：

- 「DNS服务器」 / 「修改DNS」 / 「DNS修改」
- 或「域名DNS」标签页

进去后一般有两种模式：

| 选项 | 说明 |
|---|---|
| 使用西部数码默认DNS | 不要选（就是现在的状态） |
| 使用其他DNS / 自定义DNS | 选这个 |

选中「使用其他DNS / 自定义DNS」后，出现 DNS1 / DNS2 两个输入框。
把第 0 步复制的两条 Cloudflare NS 分别填进去：

    DNS1:  aria.ns.cloudflare.com
    DNS2:  bob.ns.cloudflare.com

（换成你自己的那两条！）

注意：原来框里的 ns1.myhostadmin.net / ns2.myhostadmin.net 必须删掉，不要混合保留。

点「提交」/「保存」。

---

## 第 4 步：等待生效

- 通常 5 分钟 ~ 2 小时，最长 24~48 小时
- 西部数码若提示需要域名实名认证才能改 DNS，先完成实名

验证（PowerShell）：

    Resolve-DnsName wenhh.top -Type NS -Server 8.8.8.8

- 返回 ns1.myhostadmin.net → 还没生效，继续等
- 返回 xxx.ns.cloudflare.com → 成功

再验证隧道域名：

    Resolve-DnsName runfit.wenhh.top -Server 8.8.8.8

返回 Cloudflare 的 IP（104.x / 172.67.x 段）即整条链路通了。

---

## 第 5 步：NS 生效后要做什么

几乎什么都不用做。确保这两样在跑：

    窗口1：cd D:\GRF ; python -m uvicorn app.main:app --host 0.0.0.0 --port 7788
    窗口2：cloudflared tunnel run runfit

然后打开 https://runfit.wenhh.top

---

## 常见问题

Q：Cloudflare 面板一直显示"没有DNS记录"，要加一条吗？
A：不用。runfit.wenhh.top → 隧道的 CNAME 已由 cloudflared tunnel route dns 自动建好，NS 生效后会自动出现。

Q：能不能不改 NS，只加一条 CNAME？
A：不能。Cloudflare 免费版不支持部分接入（Partial/CNAME setup），必须整域迁 NS。

Q：改 NS 会不会影响原有网站/邮箱？
A：如果 wenhh.top 现在没跑网站、没有企业邮箱，就没影响。若有，需先在 Cloudflare 补齐 A / MX / TXT 记录。

Q：改完 NS，原来的解析记录还在吗？
A：不在。NS 一换，解析完全由 Cloudflare 接管，西部数码那边配的记录全部失效。

---

## 当前服务端状态（已就绪）

| 项目 | 状态 |
|---|---|
| 隧道 runfit | 已建立，4 条连接 Registered（lax01 / lax11） |
| 隧道 ID | 7ef935d8-55aa-40e7-a20c-8e7c55a99a98 |
| config.yml | runfit.wenhh.top → http://127.0.0.1:7788 |
| cert.pem | 已存在（已登录，无需重复 login） |
| Cloudflare 内部 DNS 记录 | 已自动配置 |
| 连通性预检 | DNS / UDP / TCP / API 全 PASS |
| 后端 7788 | health 200，llm_configured=true |

唯一等待项：西部数码改 NS。