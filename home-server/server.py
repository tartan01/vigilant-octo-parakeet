"""轻量本地 HTTP 服务：托管 site/ 目录，附带访问统计与信息接口。"""
import json
import os
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SITE_DIR = BASE_DIR / "site"
LOG_DIR = BASE_DIR / "logs"
VISITS_FILE = LOG_DIR / "visits.jsonl"
PORT = 8080

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def log_message(self, fmt, *args):
        pass  # 静默，自己写结构化日志

    def do_GET(self):
        if self.path.startswith("/api/info"):
            fwd = self.headers.get("X-Forwarded-For", "")
            ip = fwd.split(",")[0].strip() if fwd else self.client_address[0]
            self._send_json({"ip": ip, "time": datetime.now().isoformat(timespec="seconds")})
            self._record(ip)
            return
        if self.path.startswith("/api/stats"):
            count = 0
            if VISITS_FILE.exists():
                with VISITS_FILE.open("r", encoding="utf-8") as f:
                    count = sum(1 for _ in f)
            self._send_json({"visits": count})
            return
        super().do_GET()

    def _send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record(self, ip):
        LOG_DIR.mkdir(exist_ok=True)
        with VISITS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ip": ip,
                "time": datetime.now().isoformat(timespec="seconds"),
                "path": self.path,
                "ua": self.headers.get("User-Agent", ""),
            }, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Serving {SITE_DIR} on http://0.0.0.0:{PORT}", flush=True)
    server.serve_forever()
