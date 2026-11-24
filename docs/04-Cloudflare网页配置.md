# 04 — Cloudflare 网页配置

> 这部分必须由登录账号的用户本人在网页操作，Agent 无法代劳（需要账号授权）。
> 完整原始指南见项目内 `Cloudflare配置步骤.md`。

## 现状

- 账号：用户已有 Cloudflare 账号
- 域名：`honoweb.com`，NS 已托管到 Cloudflare，状态 Active
- 隧道：`home-server`，已创建并连通
- Public Hostname：已配置 `www.honoweb.com → HTTP 127.0.0.1:8080`

## 完整配置路径（供复现或新增服务时参考）

### 域名接入（已完成，仅当需要新增域名时重做）

1. 登录 https://dash.cloudflare.com
2. 左侧「网站 / Websites」→「添加站点 / Add a site」
3. 输入域名 → 选 Free 计划
4. Cloudflare 扫描现有解析 → 确认
5. 记下给出的两个 nameserver
6. 到域名注册商后台把 NS 改成这两个
7. 回 Cloudflare 点「检查名称服务器」，等状态变 Active

### 创建隧道（已完成）

1. 左侧「Zero Trust」→ 首次进入选 Free 计划
2. 「网络 / Networks」→「隧道 / Tunnels」
3. 「创建隧道 / Create a tunnel」→ 类型选 Cloudflared
4. 命名（本项目为 `home-server`）→ 保存
5. 选 Windows 环境，复制带 Token 的安装命令
6. 执行后连接器状态变 HEALTHY 即连通

### 配置 Public Hostname（已完成，新增服务时照此做）

在隧道页面点「公开主机名 / Public Hostname」→「添加」：

| 字段 | 本项目值 |
|---|---|
| Subdomain | `www` |
| Domain | `honoweb.com` |
| Path | 留空 |
| Service Type | HTTP |
| URL | `127.0.0.1:8080` |

保存后 `https://www.honoweb.com` 即转发到本机 8080。

**新增服务的模板**：
```
api.honoweb.com   → HTTP → 127.0.0.1:3000
files.honoweb.com → HTTP → 127.0.0.1:8082
```
一条 Public Hostname 对应一个本地端口。

### 可选的访问保护（未实施）

Zero Trust → Access → Applications → Add application → Self-hosted，
填入域名和邮箱策略，可给管理后台加邮箱 OTP 登录。免费版支持 50 用户。

## DNS 记录原理（排障用）

命名隧道会生成 `<UUID>.cfargotunnel.com` 子域。Public Hostname 本质上是在 Cloudflare DNS 建一条：
```
类型: CNAME
名称: www
目标: <隧道UUID>.cfargotunnel.com
```
官方确认：同一隧道的所有 hostname 共用这个 CNAME 目标。若手动改 DNS，目标写错会导致 1033 错误。

常见错误码：
- `1033` / `1016`：隧道未连通或 CNAME 目标错误
- 页面能开但图片加载失败：内网服务把资源地址写死成 `127.0.0.1`，应改用相对路径
