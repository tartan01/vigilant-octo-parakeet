"""SIGNAL - digital information store, HTTP / Controller layer.

Zero third-party dependencies. Layering (mirrors java-console/):
    server.py   Controller  - routing, request/response, auth guards
    console.py  Service     - admin auth, uploads, catalog & order rules
    store.py    Repository  - JSON / SQLite / MySQL / PostgreSQL

API
---
  MEMBER / PUBLIC
    GET  /api/status              health + counters + DB backend
    GET  /api/delivery-methods    the five fulfilment modes
    GET  /api/brief               the ultra-short fintech brief (homepage)
    GET  /api/me                  current session
    POST /api/send-code           email verification code (demo returns it)
    POST /api/verify              verify -> register/login, set cookie
    POST /api/logout              clear session
    GET  /api/products            public catalogue (SENSITIVE FIELDS STRIPPED)
    GET  /api/products/<id>       single public product
    POST /api/orders              create order + auto-fulfil (login required)
    GET  /api/orders              my orders incl. delivery payload
    GET  /api/download            secure file delivery (owner only)

  ADMIN CONSOLE  (independent username/password session, cookie `csid`)
    POST /api/admin/login         {username, password}
    POST /api/admin/logout
    GET  /api/admin/session
    POST /api/admin/password      change own password
    GET  /api/admin/overview      dashboard counters
    GET  /api/admin/products      full catalogue incl. hidden
    POST /api/admin/products      create
    PUT  /api/admin/products/<id> update
    DELETE /api/admin/products/<id>
    GET  /api/admin/orders
    PUT  /api/admin/orders/<id>   mark status / append note
    POST /api/admin/upload        base64 image / file upload
    GET  /api/admin/uploads       recent uploads

  PAGES
    /            storefront (Apple-style)
    /admin       admin console (typical Java-web back office)

Email sending is still in demo mode; see RESEND配置指南.md.
"""
import json
import os
import re
import secrets
import time
import urllib.parse
from datetime import datetime
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import console as console_svc
from store import (get_store, backend_name, public_product,
                   DELIVERY_METHODS, PRODUCT_FIELDS)

BASE = Path(__file__).resolve().parent
SITE = BASE / "site"
UPLOADS = BASE / "uploads"
DATA = BASE / "data"
PORT = int(os.environ.get("PORT", "8080"))

SESSIONS = {}       # member token -> email (in-memory; move to Redis/DB in production)
CODES = {}          # email -> {"code", "expires"}
LAST_SEND = {}      # email -> timestamp

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
CODE_TTL = 300
SEND_INTERVAL = 60

ADMIN_EMAILS = {
    e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()
}

DELIVERY_INFO = [
    {"key": "doc", "name": "文档发货", "en": "Document",
     "desc": "付款后立即生成下载链接，PDF / Markdown / ZIP 直接到手。"},
    {"key": "email", "name": "邮件发货", "en": "Email",
     "desc": "把文件与说明发到你指定的邮箱，留档可查。"},
    {"key": "link", "name": "私密外链", "en": "Private link",
     "desc": "交付私密链接与提取码，适合网盘与在线文档。"},
    {"key": "code", "name": "授权码", "en": "Licence code",
     "desc": "即时发放一次性授权码 / 卡密，用于开通订阅或软件。"},
    {"key": "online", "name": "站内查阅", "en": "Read online",
     "desc": "无需下载，在「我的订单」里直接阅读全文，随时回看。"},
]
DELIVERY_NAME = {d["key"]: d["name"] for d in DELIVERY_INFO}
ENABLED_BY_KEY = {d["key"]: d for d in DELIVERY_INFO}

# The fintech brief shown on the homepage Black Stage. Deliberately very short.
BRIEF_CARD = {
    "title": "金融科技信息简报 · 第 01 期",
    "lead": "把噪声折叠起来，只留下能改变判断的那几条。",
    "sourcesLabel": "信息源分享",
    "sources": [
        "一手源优先：监管公告、交易所披露、发行人文件。",
        "为每个源标注更新频率 / 口径 / 滞后。",
        "建一份可回溯清单：来源、时间、校验人。",
    ],
    "aiLabel": "AI 信息分享",
    "ai": [
        "让模型做抽取与对齐，不让它做结论。",
        "每条输出都带原文出处；无出处，即丢弃。",
        "提示词与版本入库，结果才可复现。",
    ],
    "foot": "信息差不在更多，而在更快被验证。",
}


def send_code(email, code):
    """Send the verification code. Demo writes to stdout and returns True.

    Replace with Resend / SMTP / a mail API here; keep returning True/False.
    """
    print(f"[MAIL-DEMO] to={email} code={code}", flush=True)
    return True


def is_admin(email, user=None):
    if not email:
        return False
    if email.lower() in ADMIN_EMAILS:
        return True
    u = user if user is not None else get_store().get_user(email)
    return bool(u and u.get("role") == "admin")


# --------------------------------------------------------------- fulfilment ---
def build_deliveries(order_id, lines, method, target, product_lookup):
    """Create one delivery payload per purchased item.

    If an item does not support the chosen method, fall back to its first
    enabled method and flag it, so the buyer always receives something.
    """
    out = []
    for line in lines:
        pid = line["id"]
        p = product_lookup.get(pid) or {}
        enabled = p.get("delivery") or ["doc"]
        actual = method if method in enabled else enabled[0]
        rec = {"itemId": pid, "name": p.get("name", "数字文件"),
               "method": actual, "methodName": DELIVERY_NAME.get(actual, actual)}
        if actual != method:
            rec["fallback"] = True
        if actual == "doc":
            rec["kind"] = "doc"
            rec["fileName"] = _safe_filename(p.get("name", "digital-file")) + ".md"
            rec["url"] = "/api/download?order=%s&item=%s" % (
                urllib.parse.quote(order_id), urllib.parse.quote(pid))
            rec["note"] = "点击下载，链接仅对你本人有效。"
        elif actual == "email":
            rec["kind"] = "email"
            rec["to"] = target
            rec["subject"] = "【SIGNAL】你的数字文件已送达 · " + str(p.get("name", ""))
            rec["status"] = "queued"
            rec["note"] = "已排入邮件队列（当前为演示模式，接入邮件服务后自动发送）。"
            rec["preview"] = (p.get("content") or p.get("sample") or p.get("description") or "")[:600]
        elif actual == "link":
            rec["kind"] = "link"
            rec["url"] = p.get("linkUrl") or ""
            rec["code"] = p.get("linkCode") or ""
            rec["note"] = "私密链接与提取码，请勿公开分享。"
        elif actual == "code":
            rec["kind"] = "code"
            rec["code"] = get_store().take_code(pid)
            rec["note"] = "一次性授权码，请妥善保存。"
        elif actual == "online":
            rec["kind"] = "online"
            rec["content"] = p.get("content") or p.get("sample") or ""
            rec["note"] = "全文已解锁，可随时回来查阅。"
        out.append(rec)
    return out


def _safe_filename(name):
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]", "_", str(name))[:60] or "file"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    # ---------------- helpers ----------------
    def _json(self, obj, status=200, extra_headers=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length or length > 16 * 1024 * 1024:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def _cookie(self, name):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        morsel = cookie.get(name)
        return morsel.value if morsel else None

    def _session(self):
        return SESSIONS.get(self._cookie("session") or "")

    def _admin(self):
        auth, _, _, _ = console_svc.services()
        return auth.user(self._cookie("csid"))

    # ---------------- static ----------------
    def _serve_static(self, path):
        if path in ("/", ""):
            path = "/index.html"
        if path in ("/admin", "/admin/"):
            path = "/admin.html"
        target = (SITE / path.lstrip("/")).resolve()
        if path.startswith("/uploads/"):
            target = (UPLOADS / path[len("/uploads/"):]).resolve()
            if not str(target).startswith(str(UPLOADS.resolve())) or not target.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
        elif not str(target).startswith(str(SITE.resolve())) or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        ext = target.suffix.lower()
        types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".mjs": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml", ".ico": "image/x-icon",
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".gif": "image/gif",
            ".json": "application/json; charset=utf-8",
            ".pdf": "application/pdf", ".zip": "application/zip",
            ".md": "text/markdown; charset=utf-8", ".txt": "text/plain; charset=utf-8",
            ".csv": "text/csv; charset=utf-8",
            ".woff2": "font/woff2", ".woff": "font/woff",
        }
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", types.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._json({"ok": True})

    def do_HEAD(self):
        self._serve_static(urlparse(self.path).path)

    # ---------------- GET ----------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)
        store = get_store()

        if path == "/api/status":
            visits = 0
            vfile = BASE.parent / "logs" / "visits.jsonl"
            if vfile.exists():
                try:
                    visits = sum(1 for _ in vfile.open(encoding="utf-8"))
                except Exception:
                    pass
            return self._json({
                "ok": True, "service": "signal-shop",
                "time": datetime.now().isoformat(timespec="seconds"),
                "backend": backend_name(),
                "users": store.count_users(), "products": store.count_products(),
                "orders": store.count_orders(), "visits": visits, "port": PORT,
            })

        if path == "/api/delivery-methods":
            return self._json({"ok": True, "items": DELIVERY_INFO})

        if path == "/api/brief":
            return self._json({"ok": True, "brief": BRIEF_CARD})

        if path == "/api/me":
            email = self._session()
            if not email:
                return self._json({"loggedIn": False}, 401)
            u = store.get_user(email) or {}
            return self._json({
                "loggedIn": True, "email": email,
                "name": u.get("name", ""), "role": u.get("role", "member"),
                "isAdmin": is_admin(email, u),
                "createdAt": u.get("createdAt", ""),
                "lastLogin": u.get("lastLogin", ""),
                "loginCount": u.get("loginCount", 0),
            })

        if path == "/api/products":
            items = store.list_products(
                category=(query.get("category", [""])[0]),
                q=(query.get("q", [""])[0]),
            )
            return self._json({"ok": True,
                               "items": [public_product(p) for p in items],
                               "total": len(items)})

        if path.startswith("/api/products/"):
            item = store.get_product(path.rsplit("/", 1)[-1])
            if not item:
                return self._json({"ok": False, "msg": "商品不存在"}, 404)
            return self._json({"ok": True, "item": public_product(item)})

        if path == "/api/orders":
            email = self._session()
            if not email:
                return self._json({"ok": False, "msg": "请先登录"}, 401)
            return self._json({"ok": True, "items": store.list_orders(email)})

        if path == "/api/download":
            return self._download(query)

        # ---------------- admin console ----------------
        if path == "/api/admin/session":
            u = self._admin()
            return self._json({"ok": True, "loggedIn": bool(u), "user": u or ""})

        if path.startswith("/api/admin/"):
            if not self._admin():
                return self._json({"ok": False, "msg": "后台会话已失效，请重新登录"}, 401)
            return self._admin_get(path, store)

        return self._serve_static(path)

    def _download(self, query):
        email = self._session()
        if not email:
            return self._json({"ok": False, "msg": "请先登录"}, 401)
        oid = query.get("order", [""])[0]
        pid = query.get("item", [""])[0]
        store = get_store()
        order = store.get_order(oid)
        if not order or order.get("email") != email:
            return self._json({"ok": False, "msg": "无权下载该文件"}, 403)
        allowed = any(d.get("itemId") == pid and d.get("kind") == "doc"
                      for d in (order.get("deliveries") or []))
        if not allowed:
            return self._json({"ok": False, "msg": "该订单未包含此文件的下载权限"}, 403)
        p = store.get_product(pid) or {}
        furl = str(p.get("fileUrl") or "")
        if furl.startswith("/uploads/"):
            f = (UPLOADS / furl[len("/uploads/"):]).resolve()
            if str(f).startswith(str(UPLOADS.resolve())) and f.is_file():
                body = f.read_bytes()
                fname = f.name
            else:
                body, fname = _generated_doc(p), _safe_filename(p.get("name")) + ".md"
        else:
            body, fname = _generated_doc(p), _safe_filename(p.get("name")) + ".md"
        # HTTP headers are latin-1 only. Use an ASCII fallback filename plus an
        # RFC 5987 filename* so Chinese names survive in modern browsers.
        ascii_fname = "".join(c if ord(c) < 128 and c not in '"\\' else "_" for c in fname)
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition",
                         'attachment; filename="%s"; filename*=UTF-8\'\'%s'
                         % (ascii_fname, urllib.parse.quote(fname)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _admin_get(self, path, store):
        _, storage, catalog, orders = console_svc.services()
        if path == "/api/admin/overview":
            return self._json({"ok": True, **store.overview()})
        if path == "/api/admin/products":
            return self._json({"ok": True, "items": catalog.list(True)})
        if path == "/api/admin/orders":
            return self._json({"ok": True, "items": orders.list()})
        if path == "/api/admin/uploads":
            return self._json({"ok": True, "items": storage.list()})
        self.send_error(HTTPStatus.NOT_FOUND)

    # ---------------- POST ----------------
    def do_POST(self):
        path = urlparse(self.path).path
        data = self._body()
        store = get_store()

        if path == "/api/send-code":
            email = str(data.get("email", "")).strip().lower()
            if not EMAIL_RE.match(email):
                return self._json({"ok": False, "msg": "邮箱格式不正确"}, 400)
            now = time.time()
            if now - LAST_SEND.get(email, 0) < SEND_INTERVAL:
                wait = int(SEND_INTERVAL - (now - LAST_SEND[email]))
                return self._json({"ok": False, "msg": f"请 {wait} 秒后再试"}, 429)
            code = f"{secrets.randbelow(900000) + 100000}"
            CODES[email] = {"code": code, "expires": now + CODE_TTL}
            LAST_SEND[email] = now
            if not send_code(email, code):
                return self._json({"ok": False, "msg": "邮件发送失败"}, 500)
            return self._json({"ok": True, "demoCode": code, "ttl": CODE_TTL})

        if path == "/api/verify":
            email = str(data.get("email", "")).strip().lower()
            code = str(data.get("code", "")).strip()
            rec = CODES.get(email)
            if not rec or time.time() > rec["expires"]:
                return self._json({"ok": False, "msg": "验证码已过期，请重新获取"}, 400)
            if code != rec["code"]:
                return self._json({"ok": False, "msg": "验证码不正确"}, 400)
            CODES.pop(email, None)
            now_iso = datetime.now().isoformat(timespec="seconds")
            existing = store.get_user(email)
            first_user = store.count_users() == 0
            if not existing:
                store.upsert_user(email,
                                  role="admin" if (first_user or email in ADMIN_EMAILS) else "member",
                                  createdAt=now_iso, lastLogin=now_iso, loginCount=1)
            else:
                store.upsert_user(email, lastLogin=now_iso,
                                  loginCount=int(existing.get("loginCount", 0)) + 1)
            token = secrets.token_urlsafe(32)
            SESSIONS[token] = email
            return self._json(
                {"ok": True, "email": email, "isAdmin": is_admin(email)},
                extra_headers={"Set-Cookie": f"session={token}; Path=/; HttpOnly; "
                                             f"SameSite=Lax; Max-Age=604800"})

        if path == "/api/logout":
            token = self._cookie("session")
            if token:
                SESSIONS.pop(token, None)
            return self._json(
                {"ok": True},
                extra_headers={"Set-Cookie": "session=; Path=/; Max-Age=0; "
                                             "HttpOnly; SameSite=Lax"})

        if path == "/api/orders":
            return self._create_order(data, store)

        # ---------------- admin console ----------------
        if path == "/api/admin/login":
            auth, _, _, _ = console_svc.services()
            token = auth.login(data.get("username"), data.get("password"))
            if not token:
                return self._json({"ok": False, "msg": "账号或密码不正确"}, 401)
            return self._json(
                {"ok": True, "user": str(data.get("username"))},
                extra_headers={"Set-Cookie": f"csid={token}; Path=/; HttpOnly; "
                                             f"SameSite=Lax; Max-Age=28800"})

        if path.startswith("/api/admin/"):
            user = self._admin()
            if not user:
                return self._json({"ok": False, "msg": "后台会话已失效，请重新登录"}, 401)
            return self._admin_post(path, data, user)

        self.send_error(HTTPStatus.NOT_FOUND)

    def _create_order(self, data, store):
        email = self._session()
        if not email:
            return self._json({"ok": False, "msg": "请先登录后再结算"}, 401)
        raw = data.get("items", [])
        if not isinstance(raw, list) or not raw:
            return self._json({"ok": False, "msg": "购物车是空的"}, 400)
        method = str(data.get("deliveryMethod", "doc")).strip()
        if method not in DELIVERY_METHODS:
            return self._json({"ok": False, "msg": "不支持的发货方式"}, 400)
        target = str(data.get("deliveryTarget", "")).strip() or email

        # Always recompute price from the catalogue - never trust client totals.
        lines, total, lookup = [], 0.0, {}
        for line in raw:
            pid = str(line.get("id", ""))
            qty = max(1, min(99, int(line.get("qty", 1) or 1)))
            p = store.get_product(pid)
            if not p or int(p.get("hidden", 0)):
                return self._json({"ok": False, "msg": f"商品 {pid} 已下架"}, 400)
            stock = int(p.get("stock", -1))
            if stock != -1 and stock < qty:
                return self._json({"ok": False, "msg": f"「{p.get('name')}」库存不足"}, 400)
            subtotal = float(p["price"]) * qty
            total += subtotal
            lines.append({"id": pid, "name": p.get("name"), "price": float(p["price"]),
                          "qty": qty, "subtotal": round(subtotal, 2)})
            lookup[pid] = p

        oid = "ORD" + datetime.now().strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()
        deliveries = build_deliveries(oid, lines, method, target, lookup)
        order = store.create_order(
            email, lines, total, id=oid,
            deliveryMethod=method, deliveryTarget=target,
            deliveries=deliveries, status="delivered",
            fulfilledAt=datetime.now().isoformat(timespec="seconds"),
        )
        return self._json({"ok": True, "order": order}, 201)

    def _admin_post(self, path, data, user):
        auth, storage, catalog, orders = console_svc.services()
        if path == "/api/admin/logout":
            auth.logout(self._cookie("csid"))
            return self._json({"ok": True},
                              extra_headers={"Set-Cookie": "csid=; Path=/; Max-Age=0; "
                                                           "HttpOnly; SameSite=Lax"})
        if path == "/api/admin/password":
            ok, msg = auth.change_password(user, data.get("old"), data.get("new"))
            return self._json({"ok": ok, "msg": msg}, 200 if ok else 400)
        if path == "/api/admin/upload":
            url, err = storage.save(data.get("filename"), data.get("data", ""))
            if err:
                return self._json({"ok": False, "msg": err}, 400)
            return self._json({"ok": True, "url": url}, 201)
        if path == "/api/admin/products":
            item, err = catalog.save(data)
            if err:
                return self._json({"ok": False, "msg": err}, 400)
            return self._json({"ok": True, "item": item}, 201)
        self.send_error(HTTPStatus.NOT_FOUND)

    # ---------------- PUT / DELETE ----------------
    def do_PUT(self):
        path = urlparse(self.path).path
        data = self._body()
        if not path.startswith("/api/admin/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        user = self._admin()
        if not user:
            return self._json({"ok": False, "msg": "后台会话已失效，请重新登录"}, 401)
        _, _, catalog, orders = console_svc.services()
        if path.startswith("/api/admin/products/"):
            item, err = catalog.save(data, path.rsplit("/", 1)[-1])
            if err:
                return self._json({"ok": False, "msg": err}, 400 if "不存在" not in err else 404)
            return self._json({"ok": True, "item": item})
        if path.startswith("/api/admin/orders/"):
            o = orders.mark(path.rsplit("/", 1)[-1],
                            str(data.get("status", "delivered")),
                            str(data.get("note", "")))
            if not o:
                return self._json({"ok": False, "msg": "订单不存在"}, 404)
            return self._json({"ok": True, "order": o})
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/admin/products/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not self._admin():
            return self._json({"ok": False, "msg": "后台会话已失效，请重新登录"}, 401)
        _, _, catalog, _ = console_svc.services()
        ok = catalog.delete(path.rsplit("/", 1)[-1])
        return self._json({"ok": ok} if ok else {"ok": False, "msg": "商品不存在"},
                          200 if ok else 404)


def _generated_doc(p):
    """Fallback deliverable when no real file was uploaded."""
    text = (p.get("content") or p.get("sample") or p.get("description") or "")
    header = "# %s\n\n> SIGNAL · 数字信息交付\n> %s\n\n" % (
        p.get("name", "数字文件"),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    return (header + text + "\n\n---\n本文件由 SIGNAL 自动生成，仅限购买者本人使用。\n").encode("utf-8")


if __name__ == "__main__":
    store = get_store()
    console_svc.services()
    print(f"SIGNAL shop running on http://0.0.0.0:{PORT} "
          f"(backend={backend_name()}, products={store.count_products()})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
