# SIGNAL Java Console — 典型 Web Java 端后台

标准的 Spring Boot 3.2 / Java 17 / Maven 工程。实现**管理员登录后台 + 上传图片 + 商品/订单管理**，与 Python 前台共用同一套数据契约。

> ⚠️ **验证状态**：当前这台服务器**没有安装 JDK / Maven / Gradle**（实测 `java`、`javac`、`mvn`、`gradle` 均 command not found），因此本工程**未在本机编译运行**。它是一份结构完整、可直接构建的标准源码，用于「把生意做大规模」时平移。当前**线上实际运行的是 `../server.py`（Python）**，功能与本工程一一对应且已实跑验证。

---

## 1. 为什么是「两套」

| | Python 实现（当前线上） | Java 实现（本工程，规模化路径） |
|---|---|---|
| 位置 | `../server.py` `../console.py` `../store.py` | `java-console/` |
| 端口 | 8080（Cloudflare Tunnel 指向） | 8081（可反向代理 `/admin`、`/api/admin/*`） |
| 运行条件 | Python 3.13，零依赖 | JDK 17 + Maven |
| 存储 | JSON / SQLite / MySQL / PostgreSQL | H2（默认）/ MySQL |
| 状态 | ✅ 已上线、已验证 | 📦 源码就绪，需装 JDK 后构建 |

**关键点：两边表结构、字段名、API 路径完全一致**，所以长大后可以把 Python 前台 + Java 后台指向**同一个 MySQL 库**，无需迁移数据、无需改字段。

---

## 2. 分层映射（1:1）

| 层 | Python | Java（本工程） |
|---|---|---|
| Controller / 路由 | `server.py` → `Handler` | `web/*Controller.java` → `@RestController` |
| Service / 业务 | `console.py` → `AuthService` `CatalogService` `StorageService` `OrderService` | `service/*Service.java` → `@Service` |
| Repository / 持久化 | `store.py` → `JsonStore` `SQLiteStore` `MySQLStore` `PostgresStore` | `repository/ShopRepository.java` `AdminRepository.java` → `@Repository` + `JdbcTemplate` |
| 会话 / 权限 | `AuthService` + `csid` cookie | `AuthService` + `AdminInterceptor` + `csid` cookie |
| 密码 | PBKDF2-HMAC-SHA256（20 万次） | BCrypt（`BCryptPasswordEncoder`） |
| 实体 | dict / DDL | `model/Product.java` `model/ShopOrder.java`（Java record） |

### API 契约（两边路径与载荷相同）

```
POST   /api/admin/login       {username,password}   -> Set-Cookie: csid
POST   /api/admin/logout
GET    /api/admin/session
POST   /api/admin/password    {old,new}
GET    /api/admin/overview
GET    /api/admin/products
POST   /api/admin/products
PUT    /api/admin/products/{id}
DELETE /api/admin/products/{id}
GET    /api/admin/orders
PUT    /api/admin/orders/{id} {status,note}
POST   /api/admin/upload      {filename,data(base64)}
GET    /api/admin/uploads

GET    /api/status  /api/products  /api/products/{id}
GET    /api/delivery-methods  /api/brief
POST   /api/orders  GET /api/download?order=&item=
```

前台 `site/index.html` / `site/app.js` **不需要改动**，把请求指到 8081 即可由 Java 端完整驱动。

---

## 3. 数据库契约

表名与列名与 `../store.py` 的 `DDL` 完全一致：

```
users(email PK, name, role, created_at, last_login, login_count)
products(id PK, name, subtitle, description, price, category, cover, badge,
         stock, hidden, created_at, format, delivery, size, author, sample,
         content, file_url, link_url, link_code, code_pool, email_template)
orders(id PK, email, items, total, status, created_at,
       delivery_method, delivery_target, deliveries, fulfilled_at)
console_admins(username PK, password_hash, created_at)   # Java 后台独立账号表
```

- `delivery` / `code_pool` / `items` / `deliveries` 在库里都是 **JSON 字符串**（与 Python 一致），Repository 负责序列化。
- `console_admins` 是 Java 后台自己的管理员表，不放进公开的 `users` 表。
- H2 版建表脚本：`src/main/resources/schema-h2.sql`。

### 五种发货方式

`doc` 文档下载 · `email` 邮件发货 · `link` 私密外链 · `code` 授权码 · `online` 站内在线查阅。
`service/FulfillmentService.java` 是 `server.py::build_deliveries` 的 Java 孪生实现，含「商品不支持所选方式时自动降级」逻辑。

---

## 4. 启动

### 前置

安装 **JDK 17** 与 **Maven 3.8+**：

```bash
java -version     # 应显示 17.x
mvn -v
```

### 默认：H2 内嵌库（零安装数据库，直接看效果）

```bash
cd java-console
mvn spring-boot:run
# 打开 http://127.0.0.1:8081/api/status
```

首次启动会：
1. 自动建表、写入 6 个示例数字商品；
2. 生成**随机**管理员初始密码，写入 `data/admin-credentials-java.txt`（已 gitignore），控制台会打印路径。

### 生产：与 Python 前台共用 MySQL

```bash
# 先让 Python 前台用 MySQL 后端建好表（会自动建表 + 播种）
#   DB_BACKEND=mysql DB_HOST=... DB_USER=... DB_PASSWORD=... DB_NAME=shop python ../server.py

export DB_HOST=127.0.0.1 DB_PORT=3306 DB_USER=shop DB_PASSWORD=*** DB_NAME=shop
mvn spring-boot:run -Dspring-boot.run.profiles=mysql
```

`mysql` profile 设了 `spring.sql.init.mode=never`，不会重复建表或覆盖数据。

### 打包部署

```bash
mvn clean package -DskipTests
java -jar target/signal-console-1.0.0.jar --spring.profiles.active=mysql
```

---

## 5. 接入 Cloudflare Tunnel（规模化时）

当前 `www.honoweb.com → 127.0.0.1:8080`（Python）。若要让 Java 后台接管管理端，在 Cloudflare Zero Trust 增加一条 Public Hostname，或在本机用 Caddy/Nginx 反代：

```nginx
# 示意：把管理端路径导向 Java，其余仍走 Python
location /admin      { proxy_pass http://127.0.0.1:8081; }
location /api/admin/ { proxy_pass http://127.0.0.1:8081; }
location /uploads/   { proxy_pass http://127.0.0.1:8081; }   # 或共享同一目录
location /           { proxy_pass http://127.0.0.1:8080; }
```

两边 `upload-dir` 都指向 `membersite/uploads/`，图片上传后前台立即可见。

---

## 6. 安全说明

- 密码 **BCrypt 哈希**存储，代码与仓库中没有任何明文凭据；初始密码随机生成后仅落在本机受保护文件。
- 后台会话为服务端内存会话（默认 8 小时），规模化时可替换为 Spring Session + Redis。
- `/api/admin/**` 由 `AdminInterceptor` 统一拦截，仅 `login` / `session` 放行。
- 商品公开接口经 `Product.publicView()` 脱敏，`content` / `codePool` / `linkCode` / `linkUrl` / `fileUrl` 不会外泄。
- 上传限制：白名单扩展名、单文件 ≤ 10 MB、文件名随机化（防穿越 / 覆盖）。

---

## 7. 未验证项（诚实清单）

- 本机无 JDK / Maven，本工程**未编译、未运行**；请在装有 JDK 17 的机器上执行 `mvn spring-boot:run` 做首次构建。
- 与 MySQL 的实连、`mysql` profile 的连通性未验证（需要真实数据库）。
- Spring Security 全套（方法级鉴权、CSRF、OAuth2）未引入；当前用轻量 `AdminInterceptor` + BCrypt，符合演示与中小规模，超大团队可升级为完整 Spring Security。
- 邮件发货仍是「排入队列」的演示状态，接 Resend / SMTP 后才会真实发出（与 Python 版一致，见 `../RESEND配置指南.md`）。
