# vigilant-octo-parakeet · 全量接手包

> **一句话**：拉下这个仓库，就能完整接手「把 Windows 本机做成公网服务器 → 部署动态网站 → 运营数字商品独立站」这条任务线——**从 2026-11-19 第一条需求到 2026-11-24 当前线上版本的全部上下文、配置文档与网站源码**。
>
> 打包时间：2026-11-24 16:25 (GMT+8) ｜ 目标：下一个 Agent `git clone` 后无需追问历史即可继续。

---

## 当前线上状态（打包时已核对）

| 项 | 值 |
|---|---|
| 公网地址 | `https://www.honoweb.com` |
| 链路 | Cloudflare Tunnel → `127.0.0.1:8080` → `membersite/server.py` |
| 域名 | `honoweb.com`（NS 托管到 Cloudflare） |
| 隧道 | `home-server`，ID `7f0144b7-78d9-4beb-9682-daecb68011d3` |
| 站点 | **SIGNAL** — Apple 风格 · 虚拟信息 / 数字文件独立站 |
| 不是 | ❌ 早期测试页 ❌ 新艺术运动风艺术音乐站 ❌ 青屿 VERDANT 清新风实物站 |
| 业务 | 6 个数字商品 + 5 种发货方式（文档 / 邮件 / 私密外链 / 授权码 / 站内查阅） |
| 后台 | `/admin`，独立管理员账号密码登录，可上传图片、管理商品与订单 |
| 开机自启 | `HomeServer-BootStart`（SYSTEM / AtStartup / Highest） |
| 启动器 | `home-server/launch.ps1`（内置防重复锁） |
| 运行时 | Python 3.13、Node 22；**无 JDK / Maven / Gradle / Docker** |
| 代码镜像仓库 | `git@github.com:tartan01/reimagined-doodle.git` @ `ecd737f` |
| 本仓库 | `git@github.com:tartan01/vigilant-octo-parakeet.git` |

验证命令（本机）：
```bash
curl -s https://www.honoweb.com/api/status     # 应返回 service: signal-shop
curl -s -o /dev/null -w "%{http_code}" https://www.honoweb.com/admin   # 200
```

---

## 目录导航

```
vigilant-octo-parakeet/
├── README.md                          ← 你在这里：接手总入口
├── .gitignore                         ← 防误提交密钥 / 数据
├── docs/                              ← 全部上下文与操作文档
│   ├── 00-总览与当前状态.md            ← 先看这份
│   ├── 01-需求与方案选型.md
│   ├── 02-环境准备与工具安装.md
│   ├── 03-本机网站搭建.md
│   ├── 04-Cloudflare网页配置.md
│   ├── 05-隧道接入与Token.md
│   ├── 06-开机自启配置.md
│   ├── 07-验证与排错手册.md
│   ├── 08-后续扩展路线.md
│   ├── 09-接手Agent行动指南.md
│   ├── 10-用户消息记录（脱敏）.md      ← 26 条真实用户诉求，逐条原文
│   ├── 11-对话全程归档.md              ← 结构化时间线 / 决策 / 错误修复 / 状态
│   ├── 12-敏感文件清单与获取方式.md    ← 哪些没入库、去哪拿 ★必读
│   ├── 接力提示词-新任务粘贴即用.md    ← 可直接粘给新任务的单文件提示词
│   ├── 本机服务器状态监测.html         ← 桌面监测页（读 /api/status）
│   ├── GitHub公钥-复制到GitHub.txt    ← 公钥（无害）
│   └── mainstationkey_public_key.txt  ← 公钥（无害）
└── home-server/                       ← 项目完整快照（脱敏）
    ├── bin/cloudflared.exe            ← 官方可执行文件 55,483,112 bytes
    ├── launch.ps1                     ← 主启动器（网站 + 隧道）
    ├── start-detached.ps1             ← 脱离会话拉起服务的一次性任务
    ├── install-boot-startup.ps1       ← SYSTEM 开机自启安装
    ├── 一键配置开机自启.bat / 验证开机任务.bat
    ├── Cloudflare配置步骤.md / 开机自启说明.md
    ├── server.py + site/index.html    ← 早期测试页（保留作历史记录）
    └── membersite/                    ← ★ 当前线上网站全部源码
        ├── server.py / store.py / console.py
        ├── site/                      ← 前台 index.html/styles.css/app.js
        │                                + 后台 admin.html/admin.css/admin.js
        ├── java-console/              ← Spring Boot 3 + JDK 17 后台源码（未编译）
        ├── .env.example / .gitignore / README.md / RESEND配置指南.md
        └── 金融科技简报-第01期.md
```

---

## 接手 Agent 的 5 步

1. **读**：本 README → `docs/00-总览与当前状态.md` → `docs/接力提示词-新任务粘贴即用.md`。
2. **补历史**：`docs/10`（用户到底要过什么）+ `docs/11`（做过什么、踩过什么坑、为什么这么定）。
3. **查配置**：按 `docs/01`–`09` 对照本机实际文件；重点 `launch.ps1`、`install-boot-startup.ps1`、`Cloudflare配置步骤.md`。
4. **验服务**：`curl /api/status`、`netstat` 看 8080、`Get-ScheduledTask HomeServer-BootStart`、确认 `cloudflared.exe` 在跑。
5. **取凭据**：按 **`docs/12-敏感文件清单与获取方式.md`** 从本机取 Token / 管理员密码 / SSH 私钥。**仓库里没有，也不要往仓库里写。**

---

## 仓库里有什么 / 没有什么

| ✅ 已入库 | ❌ 未入库（原因见 `docs/12`） |
|---|---|
| 全部 10 份交接文档 + 接力提示词 + 监测页 | Cloudflare Tunnel Token（`token.txt`、`tunnel-token.txt`） |
| 26 条脱敏用户消息 + 全程归档 + 敏感清单 | 管理员初始密码、admins.json、用户 / 订单 / 商品运行时数据 |
| `home-server/` 全部脚本与早期测试页 | `data/`、`uploads/`、`logs/`、`_backup/` |
| `membersite/` 全量源码（含 `java-console/`） | 访问日志 `visits.jsonl`（含访客 IP）、`*.log` |
| `bin/cloudflared.exe`（55MB 官方二进制） | SSH **私钥**、桌面 `新建文件夹/`（误发的私钥） |
| `.env.example`、两份公钥、金融科技简报 | 重复的 `cloudflared-alt.exe`、嵌套 `.git/` |

> 本仓库按**公开仓库**标准处理。原始 7MB 会话 jsonl 也未入库（难以保证零残留），只提供脱敏整理版。

---

## 两个 GitHub 仓库的关系

| 仓库 | 用途 | 内容 |
|---|---|---|
| `reimagined-doodle` | **代码镜像**，持续跟随网站改版提交 | 只有 `membersite/` 网站代码，`main = ecd737f`（历史 `388ca38` → `3e440ff`） |
| `vigilant-octo-parakeet` | **全量接手包**（本仓库） | 项目快照 + 全部交接文档 + 对话记录 + 脱敏说明，**供新 Agent 一次性拉取** |

改网站代码时继续推 `reimagined-doodle`；需要把最新状态同步给接手 Agent 时，重新生成本接手包并推这里。

---

## 已知未完成 / 可选后续

- **Resend 真实邮件未接**：验证码仍是 `demoCode` 演示模式，邮件发货只排入队列不真发。配置步骤见 `home-server/membersite/RESEND配置指南.md`（域名验证、SPF/DKIM/DMARC、DNS only 灰云、API Key 环境变量）。
- **Java 端未编译运行**：本机无 JDK / Maven / Gradle。`java-console/` 是标准 Spring Boot 3 源码交付，表 / 字段 / API 与 Python 完全一致；需 JDK 17 + `mvn spring-boot:run` 才能跑。当前线上后台是 Python 三层实跑版。
- **数据库**：`store.py` 支持 `json`（默认）/ `sqlite` / `mysql` / `postgres`，SQLite 已实测建表；MySQL / PostgreSQL 适配器就绪但**未实连**。
- **管理员密码**：首次启动随机生成在 `membersite/data/admin-credentials.txt`，登录后应在后台「设置」里改掉。
- **视觉**：Apple 风格严格按用户给的规范实现，若仍有偏差可按反馈微调留白比例、字号、区块节奏。

---

## 一句话给下一个 Agent

> 线上跑的是 **SIGNAL Apple 风格数字商品站**（`www.honoweb.com` → 本机 8080 → `membersite/server.py`），
> 隧道与开机自启都已稳定，**别重做基础设施**；
> 先读 `docs/00`、`docs/11`、`docs/12`，再按用户新需求改 `membersite/`，改完推 `reimagined-doodle`。
