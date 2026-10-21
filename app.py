"""Vercel entrypoint. A plain WSGI app (no extra packages) that serves:
  POST /api/score   multipart: file, target, consent
  GET  /api/health  quick check
  GET  /            the front end page in public/ (step 5)
Vercel's current Python runtime looks for a top-level `app` in app.py."""
import json
import os

from core.rubric import MAX_FILE_BYTES, RUBRIC_VERSION
from core.service import COOKIE_NAME, MAX_BODY_BYTES, device_limit, get_store, handle_score

ROOT = os.path.dirname(os.path.abspath(__file__))
JSON_HEADERS = [("Content-Type", "application/json; charset=utf-8"), ("Cache-Control", "no-store")]


def _json(start_response, status, payload, extra=None):
    body = json.dumps(payload).encode()
    reason = {200: "OK", 400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed", 411: "Length Required",
              413: "Payload Too Large", 422: "Unprocessable Entity", 429: "Too Many Requests", 500: "Server Error"}.get(status, "OK")
    start_response(f"{status} {reason}", JSON_HEADERS + [("Content-Length", str(len(body)))] + (extra or []))
    return [body]


def _score(environ, start_response):
    length = environ.get("CONTENT_LENGTH", "")
    length = int(length) if length.isdigit() else None
    stream = environ["wsgi.input"]
    ip = (environ.get("HTTP_X_REAL_IP") or environ.get("HTTP_X_FORWARDED_FOR", "").split(",")[0] or environ.get("REMOTE_ADDR", "")).strip()
    status, payload, cookie = handle_score(environ.get("CONTENT_TYPE"), length, stream.read, environ.get("HTTP_COOKIE"), ip)
    if status == 413 and length:        # read and discard (capped) so the browser sees the message, not a dropped connection
        left = min(length, 8 * 1024 * 1024)
        while left > 0:
            chunk = stream.read(min(65536, left))
            if not chunk:
                break
            left -= len(chunk)
    extra = []
    if cookie:
        secure = "; Secure" if environ.get("HTTP_X_FORWARDED_PROTO", "https") == "https" else ""
        extra.append(("Set-Cookie", f"{COOKIE_NAME}={cookie}; Max-Age=31536000; Path=/; HttpOnly; SameSite=Lax{secure}"))
    return _json(start_response, status, payload, extra)


def _health(start_response):
    uses_upstash = type(get_store()).__name__ == "UpstashStore"
    return _json(start_response, 200, {"ok": True, "rubric_version": RUBRIC_VERSION, "mode": "rules_only",
                                       "max_file_mb": MAX_FILE_BYTES // (1024 * 1024), "uploads_per_device_per_day": device_limit(),
                                       "limit_store": "upstash" if uses_upstash else "memory (not reliable on Vercel)"})


def app(environ, start_response):
    path, method = environ.get("PATH_INFO", "/"), environ.get("REQUEST_METHOD", "GET")
    if path == "/api/score":
        if method != "POST":
            return _json(start_response, 405, {"ok": False, "error": {"code": "method_not_allowed", "message": "Use the upload page to score a CV."}})
        return _score(environ, start_response)
    if path == "/api/health" and method == "GET":
        return _health(start_response)
    if path in ("/", "/index.html") and method == "GET":
        try:
            with open(os.path.join(ROOT, "public", "index.html"), "rb") as f:
                body = f.read()
        except OSError:
            return _json(start_response, 404, {"ok": False, "error": {"code": "not_found", "message": "Page not found."}})
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]
    return _json(start_response, 404, {"ok": False, "error": {"code": "not_found", "message": "Page not found."}})
