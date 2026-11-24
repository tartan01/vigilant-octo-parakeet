# Cloudflare Tunnel 配置步骤（网页端 + 本机）

> 前提：你已有 Cloudflare 账号，且你的 `.com` 域名已添加到 Cloudflare（NS 已切换并生效）。
> 如果域名还没接入，先做第 0 步。

---

## 第 0 步（域名未接入时才做）

1. 登录 https://dash.cloudflare.com
2. 左侧菜单 **「网站 / Websites」** → **「添加站点 / Add a site」**
3. 输入你的 `.com` 域名 → 选 **Free 计划**
4. Cloudflare 扫描现有解析记录 → 确认保留
5. 页面会给出 **两个 nameserver**（形如 `xxx.ns.cloudflare.com`）
6. 去你买域名的注册商后台，把 DNS 服务器改成这两个，保存
7. 回到 Cloudflare 点「完成，检查名称服务器」，等状态变 **Active**（几分钟到几小时）

---

## 第 1 步：进入 Zero Trust

1. 登录后，左侧菜单找到 **「Zero Trust」**（可能在「更多」里，或直接可见）
2. 首次进入会要求选择套餐 → 选 **Free**（不需要绑信用卡）
3. 按提示完成初始化（可能要验证邮箱）

## 第 2 步：创建隧道

1. Zero Trust 左侧菜单：**「网络 / Networks」** → **「隧道 / Tunnels」**
2. 点 **「创建隧道 / Create a tunnel」**
3. 类型选 **「Cloudflared」**
4. 起个名字，比如 `home-server` → 点 **「保存隧道 / Save tunnel」**
5. 进入配置页，选择环境：**Windows** → 点 **「复制」** 按钮复制那条安装命令
   - 这条命令里包含 **Token**（一长串字符），形如：
     `cloudflared.exe service install eyJ...(很长的字符串)...`
   - **把这条完整命令发给我**，我会帮你在本机执行
   - 或者你自己执行也可以（见下方"本机执行"）

6. 页面下方会显示 **「连接器 / Connectors」** 状态。执行完命令后，这里会显示 **HEALTHY（绿色）**，代表隧道已连上。

> **✅ 本机已完成（2026-11-20）**：Token 已安装，隧道已建立 4 条连接（其中 3 条稳定），环境健康检查全部 PASS。请回到这个页面确认连接器状态变为 **HEALTHY**。

## 第 3 步：配置公开主机名（把域名指向本机服务）

隧道连上后，在同一页面点 **「公开主机名 / Public Hostname」** 标签 → **「添加公开主机名 / Add a public hostname」**：

| 字段 | 填写内容 |
|---|---|
| Subdomain | `www`（或你想要的子域名） |
| Domain | 选你的 `.com` 域名 |
| Path | 留空 |
| Service Type | **HTTP** |
| URL | `127.0.0.1:8080` |

点 **Save hostname**。这样 `https://www.你的域名.com` 就会转发到本机的测试网站。

> **✅ 已配置完成（2026-11-20 22:48）**：`www.honoweb.com` → `http://127.0.0.1:8080`。
> 公网验证结果：首页 HTTP 200（2.2 秒，来自 Cloudflare  Amsterdam 边缘节点），
> `/api/info` 正确返回访问者 IP，`/api/stats` 正确返回访问计数。

> 以后要加更多服务，就在同一隧道里继续添加公开主机名，每条指向不同的本地端口即可。
> 例如 `api.honoweb.com` → `http://127.0.0.1:3000`，保存后即可从公网访问。

## 第 4 步：给管理页加访问保护（可选但推荐）

1. Zero Trust 左侧：**「访问控制 / Access」** → **「应用程序 / Applications」** → **「添加应用程序 / Add an application」**
2. 选 **「自托管 / Self-hosted」**
3. 填入域名、设置名称
4. 在 **Policies** 里设置规则：Action 选 Allow，条件填你的邮箱
5. 这样外人访问会先看到邮箱验证码登录页

---

## 本机执行（与网页端配合）

收到你给的安装命令后，我会：
1. 在本机执行那条带 Token 的 `cloudflared service install` 命令（需要管理员权限时会提示你提权）
2. 创建 `config.yml` 配置文件
3. 启动服务并验证 HEALTHY 状态
4. 用 `curl` 测试域名是否返回网站内容

---

## 你现在只需要做

打开 Cloudflare → 进 Zero Trust → 建隧道 → **把第 2 步第 5 条那条带 Token 的安装命令复制发给我**。剩下的我来。
