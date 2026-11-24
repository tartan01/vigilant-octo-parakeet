# SIGNAL — 数字信息商店（Apple 风格独立站 + 管理后台 + Java 工程）

卖**虚拟信息与数字文件**的小型商业站点。前台是 Apple 风格的商品展示与购买页，付款后**自动发货**（五种交付方式），后台有独立的管理员登录系统，另附一套标准的 Spring Boot 工程作为规模化路径。

- 线上地址：<https://www.honoweb.com>
- 管理后台：<https://www.honoweb.com/admin>
- 运行方式：本机 Python + Cloudflare Tunnel（开机自启）

---

## 1. 它是什么

| 模块 | 位置 | 说明 |
|---|---|---|
| 前台商店 | `site/index.html` `styles.css` `app.js` | Apple 风格：大量留白、单一系统蓝、500ms 缓动、每屏一件事 |
| 管理后台 | `site/admin.html` `admin.css` `admin.js` | 典型 Java Web 布局：独立账号密码登录、侧栏、指标卡、表格、拖拽上传 |
| HTTP 控制器 | `server.py` | 路由、鉴权、请求响应（对应 `@RestController`） |
| 业务服务 | `console.py` | 管理员认证、上传、商品/订单规则（对应 `@Service`） |
| 数据仓储 | `store.py` | JSON / SQLite / MySQL / PostgreSQL 四后端（对应 `@Repository`） |
| Java 工程 | `java-console/` | 同契约的 Spring Boot 3 + JDK 17 实现，见其 README |

分层严格：`server.py` 不碰文件与 SQL，只调 `console.py` / `store.py`；换数据库只需改环境变量。

---

## 2. 五种发货方式（核心）

商品都是数字信息，支持以下一种或多种交付方式，结算时选择，**下单即自动发货**：

| key | 方式 | 交付内容 |
|---|---|---|
| `doc` | 文档发货 | 生成下载链接（`/api/download`），仅购买者本人有效，可下载上传的真实文件或自动生成的文本 |
| `email` | 邮件发货 | 把文件与说明发到指定邮箱（当前演示模式排入队列，接 Resend 后真实发送） |
| `link` | 私密外链 | 交付私密链接 + 提取码 |
| `code` | 授权码 | 从码池原子弹出一个一次性授权码 / 卡密 |
| `online` | 站内查阅 | 无需下载，在「我的订单」里直接阅读全文 |

若某商品不支持所选方式，服务端**自动降级**为该商品支持的第一种，并在凭证上标注「已自动适配」，保证买家一定有东西到手。

---

## 3. 金融科技简报（内容商品）

首页黑色满屏区展示《金融科技信息简报 · 第 01 期》样刊，内容极简，只讲两块：

- **信息源分享**：一手源优先；标注更新频率/口径/滞后；可回溯清单（来源、时间、校验人）。
- **AI 信息分享**：让模型做抽取与对齐、不做结论；每条输出带出处；提示词与版本入库。

完整正文见 [`金融科技简报-第01期.md`](金融科技简报-第01期.md)，也作为商品 `d1` 的在线查阅内容。

---

## 4. 管理后台

- 入口：`/admin`
- **独立账号密码登录**，与会员的邮箱验证码登录互不影响。
- 首次启动自动生成**随机**初始密码，写入 `data/admin-credentials.txt`（已 gitignore）。💡 当前线上初始账号 `admin`，密码见该文件；登录后请到「设置」立即修改。
- 功能：概览指标、商品 CRUD（含发货方式多选、封面/交付文件上传、授权码池、在线全文、试读）、订单发货状态、图片/文件上传与素材库、修改密码。
- 密码用 **PBKDF2-HMAC-SHA256**（20 万次迭代、随机盐）存储，代码与仓库中**无任何明文凭据**。

---

## 5. 启动 / 维护

```bash
# 前台 + 后台（端口 8080）
python server.py

# 换数据库（示例）
set DB_BACKEND=sqlite          # 或 mysql / postgres
python server.py
```

开机自启由 `../HomeServer-BootStart` 计划任务负责（SYSTEM、AtStartup），调用 `../launch.ps1`。重启 web 进程：

```bash
taskkill /PID <pid> /F          # 结束占用 8080 的 pythonw
# 再通过计划任务触发 ../start-detached.ps1 或重启机器
```

---

## 6. 数据与安全

- 数据在 `data/`（JSON 文件或 SQLite），整个目录已 gitignore；上传文件在 `uploads/`，同样 gitignore。
- 公开商品接口经 `public_product()` 脱敏，`content` / `codePool` / `linkCode` / `linkUrl` / `fileUrl` **永不外泄**；只有购买者能在自己的订单里看到交付凭证。
- 下单价格由服务端按目录价重算，绝不信任客户端；下载接口校验「登录 + 订单归属 + 该商品确有 doc 权限」。

---

## 7. 规模化路径

`java-console/` 是与本实现**同表同字段同 API** 的 Spring Boot 工程。长大后可以：

1. 前台与后台都指向同一个 MySQL 库；
2. 用 Nginx/Caddy 把 `/admin`、`/api/admin/*` 反代到 Java（8081），其余仍走 Python（8080）；
3. 数据零迁移、前端零改动。

详见 [`java-console/README.md`](java-console/README.md)。

---

## 8. 尚未接入 / 待验证

- **邮件发货仍是演示模式**（排入队列，不真实发送）。接 Resend / SMTP 后才会真发，见 `RESEND配置指南.md`。
- **Java 工程未在本机编译**：这台服务器没有 JDK / Maven，工程为完整源码，需在装好 JDK 17 的机器上 `mvn spring-boot:run` 做首次构建。
- MySQL / PostgreSQL 适配器就绪但未实连（当前线上用 JSON 后端）。
