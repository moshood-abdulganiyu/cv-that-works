"""Step 4 service layer: everything the API needs that is not scoring.
Kept out of api/score.py so it can be tested locally without Vercel.
Rules: files stay in memory, nothing about a student is stored in phase 1, counters hold no CV content."""
import copy
import hashlib
import json
import os
import re
import secrets
import urllib.request
from datetime import datetime, timedelta, timezone
from email import message_from_bytes, policy

from .engine import score_file
from .reader import CVReadError
from .rubric import MAX_FILE_BYTES, TARGETS

BODY_OVERHEAD = 64 * 1024            # room for multipart framing around the file
MAX_BODY_BYTES = MAX_FILE_BYTES + BODY_OVERHEAD   # about 4.06 MB, under Vercel's 4.5 MB request limit
COOKIE_NAME = "cvtw_did"


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


# ---------- settings (trainer can change these in Vercel, no code edit) ----------
def device_limit():
    return int(os.environ.get("UPLOADS_PER_DEVICE_PER_DAY", "3"))


def ip_limit():
    # Higher on purpose: a whole class often shares one campus or hostel connection.
    return int(os.environ.get("UPLOADS_PER_IP_PER_DAY", "30"))


# ---------- multipart reading ----------
def parse_multipart(content_type, body):
    """Return ({field: text}, {field: (filename, bytes)})."""
    if not content_type or "multipart/form-data" not in content_type.lower():
        raise ApiError(400, "bad_request", "Please upload your CV using the upload page.")
    msg = message_from_bytes(b"Content-Type: " + content_type.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + body, policy=policy.HTTP)
    fields, files = {}, {}
    for part in msg.iter_parts() if msg.is_multipart() else []:
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename is not None:
            files[name] = (filename, payload)
        else:
            fields[name] = payload.decode("utf-8", errors="ignore").strip()
    return fields, files


# ---------- limits: counters only ----------
class MemoryStore:
    """Fallback for local runs and tests. On Vercel each instance has its own copy, so use Upstash there."""
    def __init__(self):
        self.d = {}

    def get_many(self, keys):
        return [self.d.get(k, 0) for k in keys]

    def incr_many(self, keys):
        for k in keys:
            self.d[k] = self.d.get(k, 0) + 1


class UpstashStore:
    """Upstash Redis over its REST API. No extra package needed."""
    def __init__(self, url, token):
        self.url, self.token = url.rstrip("/"), token

    def _pipeline(self, commands):
        req = urllib.request.Request(self.url + "/pipeline", data=json.dumps(commands).encode(),
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=2.5) as r:
            return json.loads(r.read())

    def get_many(self, keys):
        out = self._pipeline([["GET", k] for k in keys])
        return [int(x.get("result") or 0) for x in out]

    def incr_many(self, keys):
        cmds = []
        for k in keys:
            cmds += [["INCR", k], ["EXPIRE", k, 172800]]
        self._pipeline(cmds)


_MEMORY = MemoryStore()


def get_store():
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    return UpstashStore(url, token) if url and token else _MEMORY


def _today():
    return (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%d")   # Lagos day (UTC+1)


def _hash(*parts):
    salt = os.environ.get("LIMIT_SALT", "cvtw-default-salt")
    return hashlib.sha256("|".join((salt,) + parts).encode()).hexdigest()[:24]


def limit_keys(device_id, ip):
    day = _today()
    return f"cvtw:dev:{day}:{_hash('d', device_id)}", f"cvtw:ip:{day}:{_hash('i', ip)}"


def check_limit(store, device_id, ip):
    """Return uploads left today for this device. Raises ApiError when out. Fails open if the store is down,
    because the tool must keep working (a counter outage should not block students)."""
    dk, ik = limit_keys(device_id, ip)
    try:
        d, i = store.get_many([dk, ik])
    except Exception:
        return None
    if d >= device_limit() or i >= ip_limit():
        raise ApiError(429, "limit_reached",
                       f"You have used your {device_limit()} free scores for today. Fix your top three items, then come back tomorrow to upload again.")
    return device_limit() - d


def record_use(store, device_id, ip):
    try:
        store.incr_many(list(limit_keys(device_id, ip)))
    except Exception:
        pass


# ---------- privacy: what the student's browser is allowed to receive ----------
_EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d{2,4}[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}(?!\d)")


def _scrub(value):
    if isinstance(value, str):
        return _PHONE.sub("[phone]", _EMAIL.sub("[email]", value))
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    return value


def public_report(report):
    """Drop `facts` (holds email and phone) and scrub any stray email or phone in the text shown."""
    r = copy.deepcopy(report)
    r.pop("facts", None)
    return _scrub(r)


# ---------- the one request handler used by api/score.py ----------
def handle_score(content_type, content_length, read_body, cookie_header, ip, store=None):
    """Return (status, payload, new_device_id_or_None). Never raises."""
    store = store or get_store()
    device_id = None
    for chunk in (cookie_header or "").split(";"):
        k, _, v = chunk.strip().partition("=")
        if k == COOKIE_NAME and re.fullmatch(r"[A-Za-z0-9_\-]{16,40}", v):
            device_id = v
    new_cookie = None
    if not device_id:
        device_id = new_cookie = secrets.token_urlsafe(16)
    try:
        if content_length is None:
            raise ApiError(411, "bad_request", "The upload did not arrive. Please try again.")
        if content_length > MAX_BODY_BYTES:
            raise ApiError(413, "too_large", f"This file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB. Save a smaller PDF or DOCX and try again.")
        body = read_body(content_length)
        fields, files = parse_multipart(content_type, body)
        if fields.get("consent", "").lower() not in ("true", "on", "1", "yes"):
            raise ApiError(400, "missing_consent", "Please tick the box to confirm you agree before we score your CV.")
        if "file" not in files or not files["file"][1]:
            raise ApiError(400, "no_file", "Please choose your CV file (PDF or DOCX) before you press the button.")
        left = check_limit(store, device_id, ip)
        target = fields.get("target", "").strip().lower()
        target = target if target in TARGETS and target != "not sure" else None
        name, data = files["file"]
        report = score_file(name, data, target, judge=True)   # in memory only, nothing written to disk
        del data, body, files                          # file is gone once scored
        record_use(store, device_id, ip)
        return 200, {"ok": True, "result": public_report(report), "uploads_left_today": None if left is None else max(left - 1, 0),
                     "stored": False}, new_cookie
    except ApiError as e:
        return e.status, {"ok": False, "error": {"code": e.code, "message": e.message}}, new_cookie
    except CVReadError as e:
        return (413 if e.code == "too_large" else 422), {"ok": False, "error": {"code": e.code, "message": e.message}}, new_cookie
    except Exception:
        # Never echo the exception: it could contain CV text.
        return 500, {"ok": False, "error": {"code": "server_error", "message": "Something went wrong on our side. Please try again in a minute."}}, new_cookie
