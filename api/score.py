"""POST /api/score  (multipart: file, target, consent). Thin Vercel wrapper around core.service."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.service import COOKIE_NAME, handle_score  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _send(self, status, payload, cookie=None):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            secure = "; Secure" if self.headers.get("x-forwarded-proto", "https") == "https" else ""
            self.send_header("Set-Cookie", f"{COOKIE_NAME}={cookie}; Max-Age=31536000; Path=/; HttpOnly; SameSite=Lax{secure}")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = self.headers.get("Content-Length")
        ip = (self.headers.get("x-real-ip") or self.headers.get("x-forwarded-for", "").split(",")[0] or self.client_address[0]).strip()
        status, payload, cookie = handle_score(
            self.headers.get("Content-Type"), int(length) if length and length.isdigit() else None,
            lambda n: self.rfile.read(n), self.headers.get("Cookie"), ip)
        if status == 413 and length and length.isdigit():   # read and discard (capped) so the browser sees the message, not a dropped connection
            left = min(int(length), 8 * 1024 * 1024)
            while left > 0:
                chunk = self.rfile.read(min(65536, left))
                if not chunk:
                    break
                left -= len(chunk)
        self._send(status, payload, cookie)

    def do_GET(self):
        self._send(405, {"ok": False, "error": {"code": "method_not_allowed", "message": "Use the upload page to score a CV."}})

    def log_message(self, *args):   # no request logging: nothing about a student should land in logs
        pass
