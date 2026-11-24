"""Store - unified data access layer for SIGNAL (digital goods shop).

WHY THIS FILE EXISTS
--------------------
The HTTP layer (server.py) NEVER touches files or SQL directly. It only calls
methods on the object returned by get_store(). To switch database, set the
DB_BACKEND environment variable and restart - no business logic changes.

This is the Repository layer of the app. The Java Spring Boot project in
java-console/ mirrors these entities with JPA @Entity + JpaRepository.

SUPPORTED BACKENDS (DB_BACKEND)
-------------------------------
  json      (default) JSON files, zero dependency, best for local / demo.
  sqlite    SQLite file, Python stdlib, works out of the box.
  mysql     MySQL / MariaDB, requires: pip install pymysql
  postgres  PostgreSQL, requires: pip install psycopg2-binary

TABLES (same shape on every backend)
------------------------------------
  users(email PK, name, role, created_at, last_login, login_count)
  products(id PK, name, subtitle, description, price, category, cover,
           badge, stock, hidden, created_at, format, delivery(JSON), size,
           author, sample, content, file_url, link_url, link_code,
           code_pool(JSON), email_template)
  orders(id PK, email, items JSON, total, status, created_at,
         delivery_method, delivery_target, deliveries JSON, fulfilled_at)

DIGITAL GOODS MODEL
-------------------
* ``delivery`` is a list of enabled fulfilment methods:
    doc    文档发货  - downloadable file (fileUrl or generated text)
    email  邮件发货  - content pushed to the buyer's mailbox
    link   私密外链  - linkUrl + linkCode (netdisk / private page)
    code   授权码    - a licence / redeem code taken from codePool
    online 站内查阅  - full text revealed inside "My orders"
* ``content`` / ``codePool`` / ``linkCode`` / ``fileUrl`` are SENSITIVE.
  server.py strips them from every public product response; only a buyer who
  owns an order sees the fulfilled payload.
* ``stock = -1`` means unlimited (typical for virtual files).

All connection settings live in environment variables (see .env.example).
Nothing secret is ever committed to git; data/ is gitignored.
"""
from __future__ import annotations

import abc
import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE / "data")))

# Bump when the sample catalogue changes shape, so old local data is refreshed.
CATALOG_VERSION = 2


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _camel(key: str) -> str:
    parts = key.split("_")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def _snake(key: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()


# Delivery methods understood by the whole stack.
DELIVERY_METHODS = ("doc", "email", "link", "code", "online")

# Fields persisted for a product. Keep in sync with DDL below.
PRODUCT_FIELDS = (
    "id", "name", "subtitle", "description", "price", "category", "cover",
    "badge", "stock", "hidden", "createdAt", "format", "delivery", "size",
    "author", "sample", "content", "fileUrl", "linkUrl", "linkCode",
    "codePool", "emailTemplate",
)

# Only these fields may ever leave the server on a PUBLIC endpoint.
PUBLIC_PRODUCT_FIELDS = (
    "id", "name", "subtitle", "description", "price", "category", "cover",
    "badge", "stock", "hidden", "createdAt", "format", "delivery", "size",
    "author", "sample",
)

ORDER_FIELDS = (
    "id", "email", "items", "total", "status", "createdAt",
    "deliveryMethod", "deliveryTarget", "deliveries", "fulfilledAt",
)


def public_product(p: dict) -> dict:
    """Strip sensitive fulfilment payload from a product dict."""
    if not p:
        return p
    return {k: p.get(k) for k in PUBLIC_PRODUCT_FIELDS if k in p}


BRIEF = """# 金融科技信息简报 · 第 01 期

一句话：把噪声折叠起来，只留下能改变判断的那几条。

## 信息源分享
- 一手源优先：监管公告、交易所披露、发行人文件。二手解读只作导航。
- 为每个源标注「更新频率 / 口径 / 滞后」，口径比数字本身更重要。
- 建一份可回溯的清单：来源、抓取时间、校验人。三条，足矣。

## AI 信息分享
- 用模型做「抽取与对齐」，不让它做「结论」。结论留给人。
- 每条输出都带原文出处；无出处，即丢弃。
- 提示词与版本入库，结果才可复现、可审计。

## 一句话
信息差不在更多，而在更快被验证。
"""

# Sample catalogue - virtual information products, seeded on a fresh DB.
SEED_PRODUCTS = [
    {
        "id": "d1", "name": "金融科技信息简报 · 第 01 期",
        "subtitle": "信息源分享 / AI 信息分享 · 极简版",
        "description": "一页纸的金融科技简报。只讲两件事：哪些信息源值得跟，以及 AI 该在哪一步介入。适合研究者、分析师与做决策的人。",
        "price": 29.0, "category": "研究简报", "cover": "", "badge": "编辑精选",
        "stock": -1, "hidden": 0, "format": "PDF · Markdown", "size": "约 1,200 字 / 2 页",
        "author": "SIGNAL 编辑部",
        "delivery": ["doc", "email", "link", "code", "online"],
        "sample": "一句话：把噪声折叠起来，只留下能改变判断的那几条。",
        "content": BRIEF,
        "fileUrl": "", "linkUrl": "https://example.com/brief-01",
        "linkCode": "SIG-01", "codePool": [], "emailTemplate": "",
    },
    {
        "id": "d2", "name": "全球信息源清单 2026",
        "subtitle": "120+ 一手源 · 带口径与更新频率",
        "description": "按监管、市场、发行人、宏观四类整理的源清单，每条标注更新频率、口径与滞后。可导入 Notion / Excel。",
        "price": 59.0, "category": "信息源", "cover": "", "badge": "热卖",
        "stock": -1, "hidden": 0, "format": "CSV · Notion", "size": "120 条 / 6 列",
        "author": "SIGNAL Research",
        "delivery": ["doc", "email", "link", "online"],
        "sample": "一手源优先：监管公告、交易所披露、发行人文件。",
        "content": "（完整清单共 120 条，购买后在线查阅或下载 CSV。）",
        "fileUrl": "", "linkUrl": "https://example.com/sources-2026",
        "linkCode": "SRC-26", "codePool": [], "emailTemplate": "",
    },
    {
        "id": "d3", "name": "AI 信息处理工作流",
        "subtitle": "抽取 / 对齐 / 溯源 · 提示词库",
        "description": "一套可复用的提示词与流程说明：让模型做抽取与对齐，把结论留给人。含版本管理与审计要点。",
        "price": 79.0, "category": "AI 资料", "cover": "", "badge": "",
        "stock": -1, "hidden": 0, "format": "Markdown · ZIP", "size": "24 个提示词 / 5 个流程",
        "author": "SIGNAL Lab",
        "delivery": ["doc", "email", "code", "online"],
        "sample": "用模型做「抽取与对齐」，不让它做「结论」。",
        "content": "（24 个提示词与 5 段工作流，购买后在线查阅或下载 ZIP。）",
        "fileUrl": "", "linkUrl": "", "linkCode": "", "codePool": [],
        "emailTemplate": "",
    },
    {
        "id": "d4", "name": "商业文档模板包",
        "subtitle": "合同 / 报告 / 会议纪要 · 18 份",
        "description": "干净、克制、可直接改的文档模板。统一字体、层级与留白，省下反复调格式的时间。",
        "price": 39.0, "category": "文档模板", "cover": "", "badge": "",
        "stock": -1, "hidden": 0, "format": "DOCX · PDF · ZIP", "size": "18 份 / 约 6 MB",
        "author": "SIGNAL Studio",
        "delivery": ["doc", "email", "link"],
        "sample": "统一字体、层级与留白，省下反复调格式的时间。",
        "content": "", "fileUrl": "", "linkUrl": "https://example.com/templates",
        "linkCode": "TPL-18", "codePool": [], "emailTemplate": "",
    },
    {
        "id": "d5", "name": "结构化数据集 · 试用装",
        "subtitle": "清洗好的样例数据 · 含字段字典",
        "description": "已清洗、带字段字典的样例数据集，用于验证流程与建模。适合先跑通、再决定是否要全量。",
        "price": 19.0, "category": "数据集", "cover": "", "badge": "新品",
        "stock": -1, "hidden": 0, "format": "CSV · JSON", "size": "5,000 行 / 14 字段",
        "author": "SIGNAL Data",
        "delivery": ["doc", "email", "link", "code"],
        "sample": "已清洗、带字段字典的样例数据集。",
        "content": "", "fileUrl": "", "linkUrl": "https://example.com/dataset",
        "linkCode": "DATA-5K", "codePool": [], "emailTemplate": "",
    },
    {
        "id": "d6", "name": "年度订阅 · 全部简报",
        "subtitle": "每月两期 · 授权码即时开通",
        "description": "一次订阅，全年简报与信息源更新即时可用。以授权码开通，随时在站内查阅。",
        "price": 299.0, "category": "订阅", "cover": "", "badge": "",
        "stock": -1, "hidden": 0, "format": "在线授权", "size": "12 个月 / 24 期",
        "author": "SIGNAL 编辑部",
        "delivery": ["code", "online", "email"],
        "sample": "一次订阅，全年简报与信息源更新即时可用。",
        "content": "（订阅内容购买后在线查阅。）",
        "fileUrl": "", "linkUrl": "", "linkCode": "",
        "codePool": ["SIG-2026-A1", "SIG-2026-A2", "SIG-2026-A3"],
        "emailTemplate": "",
    },
]


class Store(abc.ABC):
    """The contract every backend must fulfil. All methods are thread-safe."""

    @abc.abstractmethod
    def init_schema(self) -> None: ...

    # ---- users ----
    @abc.abstractmethod
    def get_user(self, email: str): ...
    @abc.abstractmethod
    def upsert_user(self, email: str, **fields) -> dict: ...
    @abc.abstractmethod
    def list_users(self) -> list: ...
    @abc.abstractmethod
    def count_users(self) -> int: ...

    # ---- products ----
    @abc.abstractmethod
    def list_products(self, category="", q="", include_hidden=False) -> list: ...
    @abc.abstractmethod
    def get_product(self, pid: str): ...
    @abc.abstractmethod
    def create_product(self, data: dict) -> dict: ...
    @abc.abstractmethod
    def update_product(self, pid: str, data: dict): ...
    @abc.abstractmethod
    def delete_product(self, pid: str) -> bool: ...
    @abc.abstractmethod
    def count_products(self) -> int: ...
    @abc.abstractmethod
    def clear_products(self) -> None: ...
    @abc.abstractmethod
    def take_code(self, pid: str) -> str:
        """Pop one licence code from a product's pool (atomic)."""

    # ---- orders ----
    @abc.abstractmethod
    def create_order(self, email: str, items: list, total: float, **extra) -> dict: ...
    @abc.abstractmethod
    def get_order(self, oid: str): ...
    @abc.abstractmethod
    def update_order(self, oid: str, fields: dict): ...
    @abc.abstractmethod
    def list_orders(self, email=None) -> list: ...
    @abc.abstractmethod
    def count_orders(self) -> int: ...
    @abc.abstractmethod
    def revenue(self) -> float: ...

    # ---- derived ----
    def overview(self) -> dict:
        orders = self.list_orders()
        pending = sum(1 for o in orders if o.get("status") == "pending")
        return {
            "users": self.count_users(),
            "products": self.count_products(),
            "orders": len(orders),
            "revenue": round(self.revenue(), 2),
            "pending": pending,
            "recentOrders": orders[:5],
        }

    def ensure_seed(self) -> None:
        """Seed sample catalogue on a fresh DB, or refresh an outdated one."""
        allp = self.list_products(include_hidden=True)
        outdated = allp and not any("format" in p for p in allp)
        if not allp or outdated:
            if outdated:
                self.clear_products()
            for item in SEED_PRODUCTS:
                rec = dict(item)
                rec.setdefault("createdAt", now_iso())
                rec["catalogVersion"] = CATALOG_VERSION
                self.create_product(rec)


def _normalise_product(data: dict) -> dict:
    """Coerce a raw dict into a fully-shaped product record."""
    rec = {}
    for k in PRODUCT_FIELDS:
        rec[k] = data.get(k, "" if k not in ("price", "stock", "hidden",
                                             "delivery", "codePool") else
                          (0 if k in ("price", "stock", "hidden") else []))
    rec["id"] = data.get("id") or ("d" + uuid.uuid4().hex[:8])
    rec["price"] = float(data.get("price", 0) or 0)
    rec["stock"] = int(data.get("stock", -1) if data.get("stock", -1) != "" else -1)
    rec["hidden"] = int(data.get("hidden", 0) or 0)
    rec["createdAt"] = data.get("createdAt") or now_iso()
    rec["delivery"] = data.get("delivery") or ["doc", "email", "online"]
    rec["codePool"] = data.get("codePool") or []
    return rec


# ---------------------------------------------------------------- JSON ----
class JsonStore(Store):
    """Zero-dependency file backend. Files: users.json / products.json / orders.json."""

    def __init__(self):
        self._lock = threading.RLock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _path(self, name):
        return DATA_DIR / f"{name}.json"

    def _load(self, name):
        p = self._path(name)
        if not p.exists():
            return {} if name == "users" else []
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {} if name == "users" else []

    def _save(self, name, data):
        self._path(name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def init_schema(self):
        with self._lock:
            for name, default in (("users", {}), ("products", []), ("orders", [])):
                if not self._path(name).exists():
                    self._save(name, default)

    # users
    def get_user(self, email):
        with self._lock:
            return self._load("users").get(email)

    def upsert_user(self, email, **fields):
        with self._lock:
            users = self._load("users")
            rec = users.get(email) or {
                "email": email, "name": "", "role": "member",
                "createdAt": now_iso(), "lastLogin": "", "loginCount": 0,
            }
            rec.update(fields)
            rec["email"] = email
            users[email] = rec
            self._save("users", users)
            return rec

    def list_users(self):
        with self._lock:
            return list(self._load("users").values())

    def count_users(self):
        with self._lock:
            return len(self._load("users"))

    # products
    def list_products(self, category="", q="", include_hidden=False):
        with self._lock:
            items = self._load("products")
        out = []
        for it in items:
            if not include_hidden and int(it.get("hidden", 0)):
                continue
            if category and category not in ("", "all") and it.get("category") != category:
                continue
            if q and q.lower() not in (
                str(it.get("name", "")) + str(it.get("subtitle", "")) +
                str(it.get("description", ""))
            ).lower():
                continue
            out.append(it)
        return out

    def get_product(self, pid):
        with self._lock:
            return next((i for i in self._load("products") if i.get("id") == pid), None)

    def create_product(self, data):
        with self._lock:
            items = self._load("products")
            rec = _normalise_product(data)
            items.append(rec)
            self._save("products", items)
            return rec

    def update_product(self, pid, data):
        with self._lock:
            items = self._load("products")
            for i, it in enumerate(items):
                if it.get("id") == pid:
                    for k in PRODUCT_FIELDS:
                        if k in data and k != "id":
                            it[k] = data[k]
                    it["price"] = float(it.get("price", 0) or 0)
                    it["stock"] = int(it.get("stock", -1) if it.get("stock", -1) != "" else -1)
                    it["hidden"] = int(it.get("hidden", 0) or 0)
                    items[i] = it
                    self._save("products", items)
                    return it
            return None

    def delete_product(self, pid):
        with self._lock:
            items = self._load("products")
            kept = [i for i in items if i.get("id") != pid]
            if len(kept) == len(items):
                return False
            self._save("products", kept)
            return True

    def count_products(self):
        with self._lock:
            return len(self._load("products"))

    def clear_products(self):
        with self._lock:
            self._save("products", [])

    def take_code(self, pid):
        with self._lock:
            items = self._load("products")
            for it in items:
                if it.get("id") == pid:
                    pool = it.get("codePool") or []
                    code = pool.pop(0) if pool else "SIG-" + uuid.uuid4().hex[:8].upper()
                    it["codePool"] = pool
                    self._save("products", items)
                    return code
        return "SIG-" + uuid.uuid4().hex[:8].upper()

    # orders
    def create_order(self, email, items, total, **extra):
        with self._lock:
            orders = self._load("orders")
            rec = {
                "id": extra.get("id") or (
                    "ORD" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()),
                "email": email, "items": items, "total": round(float(total), 2),
                "status": extra.get("status", "delivered"),
                "deliveryMethod": extra.get("deliveryMethod", ""),
                "deliveryTarget": extra.get("deliveryTarget", ""),
                "deliveries": extra.get("deliveries", []),
                "fulfilledAt": extra.get("fulfilledAt", now_iso()),
                "createdAt": now_iso(),
            }
            orders.insert(0, rec)
            self._save("orders", orders)
            return rec

    def get_order(self, oid):
        with self._lock:
            return next((o for o in self._load("orders") if o.get("id") == oid), None)

    def update_order(self, oid, fields):
        with self._lock:
            orders = self._load("orders")
            for i, o in enumerate(orders):
                if o.get("id") == oid:
                    o.update(fields)
                    orders[i] = o
                    self._save("orders", orders)
                    return o
            return None

    def list_orders(self, email=None):
        with self._lock:
            orders = self._load("orders")
        return [o for o in orders if email is None or o.get("email") == email]

    def count_orders(self):
        with self._lock:
            return len(self._load("orders"))

    def revenue(self):
        with self._lock:
            return sum(float(o.get("total", 0)) for o in self._load("orders"))


# ------------------------------------------------------------- DB-API 2.0 ----
DDL = [
    """CREATE TABLE IF NOT EXISTS users (
        email VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) DEFAULT '',
        role VARCHAR(32) DEFAULT 'member',
        created_at VARCHAR(64),
        last_login VARCHAR(64),
        login_count INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS products (
        id VARCHAR(64) PRIMARY KEY,
        name VARCHAR(255),
        subtitle VARCHAR(255),
        description TEXT,
        price REAL DEFAULT 0,
        category VARCHAR(64),
        cover VARCHAR(512) DEFAULT '',
        badge VARCHAR(64),
        stock INTEGER DEFAULT -1,
        hidden INTEGER DEFAULT 0,
        created_at VARCHAR(64),
        format VARCHAR(128),
        delivery TEXT,
        size VARCHAR(128),
        author VARCHAR(128),
        sample TEXT,
        content TEXT,
        file_url VARCHAR(512),
        link_url VARCHAR(512),
        link_code VARCHAR(128),
        code_pool TEXT,
        email_template TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS orders (
        id VARCHAR(64) PRIMARY KEY,
        email VARCHAR(255),
        items TEXT,
        total REAL DEFAULT 0,
        status VARCHAR(32) DEFAULT 'delivered',
        created_at VARCHAR(64),
        delivery_method VARCHAR(32),
        delivery_target VARCHAR(255),
        deliveries TEXT,
        fulfilled_at VARCHAR(64)
    )""",
]

# Columns added after the first release; ALTER is best-effort (ignored if present).
DDL_MIGRATIONS = [
    "ALTER TABLE products ADD COLUMN format VARCHAR(128)",
    "ALTER TABLE products ADD COLUMN delivery TEXT",
    "ALTER TABLE products ADD COLUMN size VARCHAR(128)",
    "ALTER TABLE products ADD COLUMN author VARCHAR(128)",
    "ALTER TABLE products ADD COLUMN sample TEXT",
    "ALTER TABLE products ADD COLUMN content TEXT",
    "ALTER TABLE products ADD COLUMN file_url VARCHAR(512)",
    "ALTER TABLE products ADD COLUMN link_url VARCHAR(512)",
    "ALTER TABLE products ADD COLUMN link_code VARCHAR(128)",
    "ALTER TABLE products ADD COLUMN code_pool TEXT",
    "ALTER TABLE products ADD COLUMN email_template TEXT",
    "ALTER TABLE products ADD COLUMN cover VARCHAR(512) DEFAULT ''",
    "ALTER TABLE orders ADD COLUMN delivery_method VARCHAR(32)",
    "ALTER TABLE orders ADD COLUMN delivery_target VARCHAR(255)",
    "ALTER TABLE orders ADD COLUMN deliveries TEXT",
    "ALTER TABLE orders ADD COLUMN fulfilled_at VARCHAR(64)",
]

_JSON_COLS = {"items", "delivery", "codePool", "deliveries"}


class DbApiStore(Store):
    """Shared SQL implementation for any PEP 249 driver.

    Subclasses only provide PH (param placeholder) and _connect().
    A fresh connection is opened per operation, so it is safe with the
    ThreadingHTTPServer used by server.py.
    """

    PH = "?"

    def _connect(self):
        raise NotImplementedError

    def _run(self, sql, params=(), fetch=False, commit=False):
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            if commit:
                conn.commit()
            if fetch and cur.description:
                cols = [d[0] for d in cur.description]
                out = []
                for row in cur.fetchall():
                    d = {_camel(c): v for c, v in zip(cols, row)}
                    for jc in _JSON_COLS:
                        if jc in d and isinstance(d[jc], str):
                            try:
                                d[jc] = json.loads(d[jc])
                            except Exception:
                                d[jc] = [] if jc in ("items", "delivery", "codePool", "deliveries") else None
                    out.append(d)
                return out
            return cur.rowcount
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def init_schema(self):
        for ddl in DDL:
            self._run(ddl, commit=True)
        for ddl in DDL_MIGRATIONS:
            try:
                self._run(ddl, commit=True)
            except Exception:
                pass  # column already exists

    # users
    def get_user(self, email):
        rows = self._run(f"SELECT * FROM users WHERE email={self.PH}", (email,), fetch=True)
        return rows[0] if rows else None

    def upsert_user(self, email, **fields):
        cur = self.get_user(email)
        if cur is None:
            rec = {"email": email, "name": "", "role": "member",
                   "createdAt": now_iso(), "lastLogin": "", "loginCount": 0}
            rec.update(fields)
        else:
            rec = dict(cur)
            rec.update(fields)
        rec["email"] = email
        if cur is None:
            cols = list(rec.keys())
            sql = (f"INSERT INTO users ({','.join(_snake(c) for c in cols)}) "
                   f"VALUES ({','.join([self.PH] * len(cols))})")
            self._run(sql, tuple(rec[c] for c in cols), commit=True)
        else:
            keys = [k for k in rec if k != "email"]
            sql = (f"UPDATE users SET {','.join(f'{_snake(k)}={self.PH}' for k in keys)} "
                   f"WHERE email={self.PH}")
            self._run(sql, tuple(rec[k] for k in keys) + (email,), commit=True)
        return self.get_user(email)

    def list_users(self):
        return self._run("SELECT * FROM users ORDER BY created_at DESC", fetch=True) or []

    def count_users(self):
        r = self._run("SELECT COUNT(*) AS v FROM users", fetch=True)
        return int(r[0]["v"]) if r else 0

    # products
    def _product_from_row(self, row):
        p = dict(row)
        p["delivery"] = p.get("delivery") or []
        p["codePool"] = p.get("codePool") or []
        return p

    def list_products(self, category="", q="", include_hidden=False):
        sql = "SELECT * FROM products WHERE 1=1"
        params = []
        if not include_hidden:
            sql += " AND hidden=0"
        if category and category not in ("", "all"):
            sql += f" AND category={self.PH}"
            params.append(category)
        if q:
            sql += f" AND (name LIKE {self.PH} OR subtitle LIKE {self.PH} OR description LIKE {self.PH})"
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        sql += " ORDER BY created_at ASC"
        return [self._product_from_row(r) for r in (self._run(sql, tuple(params), fetch=True) or [])]

    def get_product(self, pid):
        r = self._run(f"SELECT * FROM products WHERE id={self.PH}", (pid,), fetch=True)
        return self._product_from_row(r[0]) if r else None

    def _sql_values(self, rec):
        cols = list(rec.keys())
        vals = []
        for c in cols:
            v = rec[c]
            if c in _JSON_COLS and not isinstance(v, str):
                v = json.dumps(v, ensure_ascii=False)
            vals.append(v)
        return cols, vals

    def create_product(self, data):
        rec = _normalise_product(data)
        cols, vals = self._sql_values(rec)
        sql = (f"INSERT INTO products ({','.join(_snake(c) for c in cols)}) "
               f"VALUES ({','.join([self.PH] * len(cols))})")
        self._run(sql, tuple(vals), commit=True)
        return rec

    def update_product(self, pid, data):
        cur = self.get_product(pid)
        if not cur:
            return None
        rec = dict(cur)
        for k in PRODUCT_FIELDS:
            if k in data and k != "id":
                rec[k] = data[k]
        rec["price"] = float(rec.get("price", 0) or 0)
        rec["stock"] = int(rec.get("stock", -1) if rec.get("stock", -1) != "" else -1)
        rec["hidden"] = int(rec.get("hidden", 0) or 0)
        cols, vals = self._sql_values({k: rec[k] for k in PRODUCT_FIELDS if k != "id"})
        sql = (f"UPDATE products SET {','.join(f'{_snake(k)}={self.PH}' for k in cols)} "
               f"WHERE id={self.PH}")
        self._run(sql, tuple(vals) + (pid,), commit=True)
        return self.get_product(pid)

    def delete_product(self, pid):
        return bool(self._run(f"DELETE FROM products WHERE id={self.PH}", (pid,), commit=True))

    def count_products(self):
        r = self._run("SELECT COUNT(*) AS v FROM products", fetch=True)
        return int(r[0]["v"]) if r else 0

    def clear_products(self):
        self._run("DELETE FROM products", commit=True)

    def take_code(self, pid):
        p = self.get_product(pid)
        pool = (p or {}).get("codePool") or []
        code = pool[0] if pool else "SIG-" + uuid.uuid4().hex[:8].upper()
        self.update_product(pid, {"codePool": pool[1:] if pool else []})
        return code

    # orders
    def create_order(self, email, items, total, **extra):
        rec = {
            "id": extra.get("id") or (
                "ORD" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()),
            "email": email, "items": items, "total": round(float(total), 2),
            "status": extra.get("status", "delivered"),
            "deliveryMethod": extra.get("deliveryMethod", ""),
            "deliveryTarget": extra.get("deliveryTarget", ""),
            "deliveries": extra.get("deliveries", []),
            "fulfilledAt": extra.get("fulfilledAt", now_iso()),
            "createdAt": now_iso(),
        }
        cols, vals = self._sql_values(rec)
        sql = (f"INSERT INTO orders ({','.join(_snake(c) for c in cols)}) "
               f"VALUES ({','.join([self.PH] * len(cols))})")
        self._run(sql, tuple(vals), commit=True)
        return rec

    def get_order(self, oid):
        r = self._run(f"SELECT * FROM orders WHERE id={self.PH}", (oid,), fetch=True)
        return r[0] if r else None

    def update_order(self, oid, fields):
        cur = self.get_order(oid)
        if not cur:
            return None
        rec = dict(cur)
        rec.update(fields)
        cols, vals = self._sql_values({k: rec[k] for k in ORDER_FIELDS if k != "id"})
        sql = (f"UPDATE orders SET {','.join(f'{_snake(k)}={self.PH}' for k in cols)} "
               f"WHERE id={self.PH}")
        self._run(sql, tuple(vals) + (oid,), commit=True)
        return self.get_order(oid)

    def list_orders(self, email=None):
        if email:
            rows = self._run(
                f"SELECT * FROM orders WHERE email={self.PH} ORDER BY created_at DESC",
                (email,), fetch=True)
        else:
            rows = self._run("SELECT * FROM orders ORDER BY created_at DESC", fetch=True)
        return rows or []

    def count_orders(self):
        r = self._run("SELECT COUNT(*) AS v FROM orders", fetch=True)
        return int(r[0]["v"]) if r else 0

    def revenue(self):
        r = self._run("SELECT COALESCE(SUM(total), 0) AS v FROM orders", fetch=True)
        return float(r[0]["v"]) if r else 0.0


class SQLiteStore(DbApiStore):
    """Works immediately, no install. DB_SQLITE_PATH sets the file location."""

    PH = "?"

    def _connect(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = Path(os.environ.get("DB_SQLITE_PATH", str(DATA_DIR / "shop.db")))
        return sqlite3.connect(str(path), timeout=10)


class MySQLStore(DbApiStore):
    """MySQL / MariaDB. Requires: pip install pymysql"""

    PH = "%s"

    def _connect(self):
        try:
            import pymysql
        except ImportError as exc:
            raise RuntimeError("DB_BACKEND=mysql needs: pip install pymysql") from exc
        return pymysql.connect(
            host=os.environ.get("DB_HOST", "127.0.0.1"),
            port=int(os.environ.get("DB_PORT", "3306")),
            user=os.environ.get("DB_USER", "root"),
            password=os.environ.get("DB_PASSWORD", ""),
            database=os.environ.get("DB_NAME", "shop"),
            charset="utf8mb4", autocommit=False,
        )


class PostgresStore(DbApiStore):
    """PostgreSQL. Requires: pip install psycopg2-binary"""

    PH = "%s"

    def _connect(self):
        try:
            import psycopg2
        except ImportError as exc:
            raise RuntimeError("DB_BACKEND=postgres needs: pip install psycopg2-binary") from exc
        return psycopg2.connect(
            host=os.environ.get("DB_HOST", "127.0.0.1"),
            port=int(os.environ.get("DB_PORT", "5432")),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", ""),
            dbname=os.environ.get("DB_NAME", "shop"),
        )


_BACKENDS = {
    "json": JsonStore,
    "sqlite": SQLiteStore,
    "mysql": MySQLStore,
    "postgres": PostgresStore,
    "postgresql": PostgresStore,
}

_STORE = None
_LOCK = threading.Lock()


def get_store() -> Store:
    """Return the process-wide Store singleton, chosen by DB_BACKEND."""
    global _STORE
    if _STORE is None:
        with _LOCK:
            if _STORE is None:
                backend = os.environ.get("DB_BACKEND", "json").strip().lower()
                cls = _BACKENDS.get(backend, JsonStore)
                store = cls()
                store.init_schema()
                store.ensure_seed()
                _STORE = store
    return _STORE


def backend_name() -> str:
    return type(_STORE).__name__ if _STORE else os.environ.get("DB_BACKEND", "json")
