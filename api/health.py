"""GET /api/health  quick check that the live link works."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.rubric import MAX_FILE_BYTES, RUBRIC_VERSION  # noqa: E402
from core.service import device_limit, get_store  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        store = type(get_store()).__name__
        body = json.dumps({"ok": True, "rubric_version": RUBRIC_VERSION, "mode": "rules_only",
                           "max_file_mb": MAX_FILE_BYTES // (1024 * 1024), "uploads_per_device_per_day": device_limit(),
                           "limit_store": "upstash" if store == "UpstashStore" else "memory (not reliable on Vercel)"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
