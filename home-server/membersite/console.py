"""console.py - Service layer for the admin console (Java-web style layering).

Layer map (mirrors java-console/ one-to-one):
    server.py            -> @RestController / DispatcherServlet (routing, HTTP)
    console.py           -> @Service  (business rules, auth, storage)
    store.py             -> @Repository / JpaRepository (persistence)

No plaintext password is ever hard-coded or committed. On first boot a random
credential is generated into data/admin-credentials.txt (gitignored). The admin
should log in once and change it from the console.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

from store import (BASE, DATA_DIR, get_store, public_product,
                   DELIVERY_METHODS, _normalise_product)

UPLOAD_DIR = BASE / "uploads"
CRED_FILE = DATA_DIR / "admin-credentials.txt"
ADMIN_FILE = DATA_DIR / "admins.json"

SESSION_TTL = 8 * 3600
MAX_UPLOAD = 10 * 1024 * 1024  # 10 MB decoded
ALLOWED_EXT = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico",
    ".pdf", ".md", ".txt", ".zip", ".csv", ".json",
    ".doc", ".docx", ".xls", ".xlsx",
}
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")


# --------------------------------------------------------------- password ---
def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return "pbkdf2$%s$%s" % (base64.b64encode(salt).decode(),
                             base64.b64encode(dk).decode())


def _check_password(password: str, stored: str) -> bool:
    try:
        _, s, d = stored.split("$", 2)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 base64.b64decode(s), 200_000)
        return hmac.compare_digest(dk, base64.b64decode(d))
    except Exception:
        return False


class AuthService:
    """Administrator accounts + server-side sessions."""

    def __init__(self):
        self._lock = threading.RLock()
        self._sessions = {}       # token -> {"user", "expires"}
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_bootstrap()

    # -- account storage --
    def _load(self):
        if not ADMIN_FILE.exists():
            return {}
        try:
            return json.loads(ADMIN_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, data):
        ADMIN_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                              encoding="utf-8")

    def _ensure_bootstrap(self):
        """First boot: create one admin with a RANDOM password, saved locally."""
        if self._load():
            return
        username = os.environ.get("ADMIN_BOOTSTRAP_USER", "admin")
        password = secrets.token_urlsafe(12)
        self._save({username: {
            "hash": _hash_password(password),
            "createdAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        }})
        CRED_FILE.write_text(
            "SIGNAL 管理后台初始凭据（请登录后立即在「设置」中修改，勿提交到 Git）\n"
            f"地址:   /admin\n"
            f"账号:   {username}\n"
            f"密码:   {password}\n"
            f"生成于: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            encoding="utf-8",
        )
        print(f"[CONSOLE] First-run admin created. Credentials: {CRED_FILE}", flush=True)

    def login(self, username, password):
        rec = self._load().get(str(username or "").strip())
        if not rec or not _check_password(str(password or ""), rec.get("hash", "")):
            return None
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[token] = {"user": username, "expires": time.time() + SESSION_TTL}
        return token

    def user(self, token):
        if not token:
            return None
        with self._lock:
            s = self._sessions.get(token)
            if not s:
                return None
            if s["expires"] < time.time():
                self._sessions.pop(token, None)
                return None
            return s["user"]

    def logout(self, token):
        with self._lock:
            self._sessions.pop(token, None)

    def change_password(self, username, old, new):
        if len(str(new or "")) < 8:
            return False, "新密码至少 8 位"
        data = self._load()
        rec = data.get(username)
        if not rec or not _check_password(str(old or ""), rec.get("hash", "")):
            return False, "原密码不正确"
        data[username] = {"hash": _hash_password(str(new)),
                          "createdAt": rec.get("createdAt", "")}
        self._save(data)
        return True, "密码已更新"


class StorageService:
    """Base64 upload -> local file. Returns a public /uploads/ URL."""

    def __init__(self):
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, data_b64: str):
        name = _SAFE_NAME.sub("_", os.path.basename(str(filename or "upload.bin")))
        ext = Path(name).suffix.lower()
        if ext not in ALLOWED_EXT:
            return None, "不支持的文件类型：" + (ext or "未知")
        try:
            raw = base64.b64decode(data_b64.split(",", 1)[-1], validate=True)
        except Exception:
            return None, "文件内容不是有效的 base64"
        if not raw or len(raw) > MAX_UPLOAD:
            return None, "文件为空或超过 10 MB"
        out = secrets.token_hex(10) + ext
        (UPLOAD_DIR / out).write_bytes(raw)
        return "/uploads/" + out, None

    def list(self):
        if not UPLOAD_DIR.exists():
            return []
        return sorted(
            [{"name": p.name, "url": "/uploads/" + p.name, "size": p.stat().st_size}
             for p in UPLOAD_DIR.iterdir() if p.is_file()],
            key=lambda x: x["name"], reverse=True)[:60]


class CatalogService:
    """Product administration.

    NOTE: the console is an authenticated admin context, so it returns the FULL
    product record (including content / codePool / linkCode / fileUrl). Only the
    public /api/products endpoint in server.py strips sensitive fields.
    """

    def list(self, include_hidden=True):
        return get_store().list_products(include_hidden=include_hidden)

    def get(self, pid):
        return get_store().get_product(pid)   # full record, admin only

    def save(self, data, pid=None):
        s = get_store()
        name = str(data.get("name", "")).strip()
        if not name:
            return None, "商品名称不能为空"
        delivery = data.get("delivery") or ["doc"]
        if isinstance(delivery, str):
            delivery = [x.strip() for x in delivery.split(",") if x.strip()]
        delivery = [d for d in delivery if d in DELIVERY_METHODS]
        if not delivery:
            return None, "至少选择一种发货方式"
        pool = data.get("codePool") or []
        if isinstance(pool, str):
            pool = [x.strip() for x in pool.replace("\n", ",").split(",") if x.strip()]
        payload = dict(data)
        payload["name"] = name
        payload["delivery"] = delivery
        payload["codePool"] = pool
        if pid:
            item = s.update_product(pid, payload)
            if not item:
                return None, "商品不存在"
            return item, None
        return s.create_product(_normalise_product(payload)), None

    def delete(self, pid):
        return get_store().delete_product(pid)


class OrderService:
    def list(self):
        return get_store().list_orders()

    def mark(self, oid, status, note=""):
        s = get_store()
        o = s.get_order(oid)
        if not o:
            return None
        fields = {"status": status}
        if note:
            deliveries = list(o.get("deliveries") or [])
            deliveries.append({"kind": "note", "text": note,
                               "at": time.strftime("%Y-%m-%d %H:%M:%S")})
            fields["deliveries"] = deliveries
        return s.update_order(oid, fields)


AUTH = None
STORAGE = None
CATALOG = None
ORDERS = None


def services():
    """Lazy singleton init (avoids touching files at import time)."""
    global AUTH, STORAGE, CATALOG, ORDERS
    if AUTH is None:
        AUTH = AuthService()
        STORAGE = StorageService()
        CATALOG = CatalogService()
        ORDERS = OrderService()
    return AUTH, STORAGE, CATALOG, ORDERS
