"""Step 8 part 2: the trainer review store and the review endpoints.
Stores ONLY redacted text, scores and each voter's output, and only when the student ticked the save box.
Never stores a name, email, phone, link, file or home address. Same Upstash database as the limit counters."""
import hmac
import json
import os
import re
import secrets
import urllib.request
from datetime import datetime, timezone

KEY_REC, KEY_IDS, KEY_FLAG = "cvtw:rev:", "cvtw:rev:ids", "cvtw:rev:flagged"
ID_RE = re.compile(r"[0-9a-f]{16}")
EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")
MAX_TEXT = 30000
LIST_LIMIT = 300


# ---------- stores ----------
class MemoryReviewStore:
    """For tests and local runs only. It forgets everything when the server restarts."""
    persistent = False

    def __init__(self):
        self.d, self.ids_, self.flag = {}, [], set()

    def save(self, rec, flagged):
        self.d[rec["id"]] = json.dumps(rec)
        self.ids_.insert(0, rec["id"])
        if flagged:
            self.flag.add(rec["id"])

    def get_many(self, ids):
        return [json.loads(self.d[i]) if i in self.d else None for i in ids]

    def ids(self, limit):
        return self.ids_[:limit]

    def flagged_ids(self):
        return list(self.flag)

    def update(self, rec):
        self.d[rec["id"]] = json.dumps(rec)
        self.flag.discard(rec["id"])

    def delete(self, i):
        self.d.pop(i, None)
        self.ids_ = [x for x in self.ids_ if x != i]
        self.flag.discard(i)


class UpstashReviewStore:
    persistent = True

    def __init__(self, url, token):
        self.url, self.token = url.rstrip("/"), token

    def _run(self, cmds):
        req = urllib.request.Request(self.url + "/pipeline", data=json.dumps(cmds).encode(),
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            out = json.loads(r.read())
        for x in out:
            if isinstance(x, dict) and x.get("error"):
                raise RuntimeError("store error")
        return [x.get("result") for x in out]

    def save(self, rec, flagged):
        cmds = [["SET", KEY_REC + rec["id"], json.dumps(rec)], ["LPUSH", KEY_IDS, rec["id"]]]
        if flagged:
            cmds.append(["SADD", KEY_FLAG, rec["id"]])
        self._run(cmds)

    def get_many(self, ids):
        out = []
        for n in range(0, len(ids), 100):
            res = self._run([["GET", KEY_REC + i] for i in ids[n:n + 100]])
            out += [json.loads(x) if x else None for x in res]
        return out

    def ids(self, limit):
        return self._run([["LRANGE", KEY_IDS, 0, limit - 1]])[0] or []

    def flagged_ids(self):
        return self._run([["SMEMBERS", KEY_FLAG]])[0] or []

    def update(self, rec):
        self._run([["SET", KEY_REC + rec["id"], json.dumps(rec)], ["SREM", KEY_FLAG, rec["id"]]])

    def delete(self, i):
        self._run([["DEL", KEY_REC + i], ["LREM", KEY_IDS, 0, i], ["SREM", KEY_FLAG, i]])


def get_review_store():
    """Upstash when it is connected. None otherwise, so nothing is claimed as saved when it is not."""
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    return UpstashReviewStore(url, token) if url and token else None


# ---------- saving (called by service.py, only when the save box is ticked) ----------
def build_record(report, text):
    cats = {}
    for k, c in report["categories"].items():
        cats[k] = {"max": c["max"], "rules": c.get("rules_total", c["points"]), "judge": c.get("judge_points"),
                   "final": c["points"], "less_certain": bool(c.get("less_certain"))}
    jd = report.get("judge") or {}
    return {
        "id": secrets.token_hex(8),
        "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "rubric_version": report.get("rubric_version"), "blend_version": report.get("blend_version"),
        "mode": report.get("mode"), "target": report.get("target"),
        "score": report.get("score"), "band": report.get("band"),
        "less_certain": list(report.get("less_certain") or []),
        "categories": cats,
        "judge": jd if jd.get("ok") else {"ok": False, "reason": jd.get("reason")},
        "text": EMAIL.sub("[email]", text)[:MAX_TEXT],
        "trainer": None,
    }


def save_for_review(report, text, store):
    """Return True only if the record really reached a lasting store. Never raises."""
    try:
        if store is None or not text or not text.strip():
            return False
        rec = build_record(report, text)
        store.save(rec, bool(rec["less_certain"]))
        return True
    except Exception:
        return False


# ---------- trainer endpoints ----------
def _auth(token):
    want = os.environ.get("REVIEW_TOKEN", "")
    if len(want) < 12:
        return 503, {"ok": False, "error": "Set REVIEW_TOKEN in Vercel (at least 12 characters) to turn on the review page."}
    if not token or not hmac.compare_digest(token.encode("utf-8", "ignore"), want.encode()):
        return 401, {"ok": False, "error": "Wrong review code."}
    return None


def _total(scores, cats):
    mx = sum(cats[k]["max"] for k in scores)
    return round(sum(scores.values()) * 100 / mx) if mx else 0


def handle_review(method, path, token, body=None, query=None, store=None):
    """Return (status, payload). Never raises. `path` ends in /api/review/<action>."""
    try:
        bad = _auth(token)
        if bad:
            return bad
        store = store or get_review_store()
        if store is None:
            return 503, {"ok": False, "error": "The review database is not connected."}
        route = "/" + path.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
        body, query = body or {}, query or {}
        if method == "GET" and route == "/list":
            ids = store.ids(LIST_LIMIT)
            flagged = set(store.flagged_ids())
            rows = []
            for r in store.get_many(ids):
                if r:
                    rows.append({"id": r["id"], "saved_at": r["saved_at"], "target": r["target"], "score": r["score"], "band": r["band"],
                                 "less_certain": r["less_certain"], "corrected": r["trainer"] is not None,
                                 "flagged": r["id"] in flagged and r["trainer"] is None})
            rows.sort(key=lambda x: (not x["flagged"], x["corrected"]))
            return 200, {"ok": True, "rows": rows, "counts": {"saved": len(rows), "waiting": sum(x["flagged"] for x in rows),
                                                            "corrected": sum(x["corrected"] for x in rows)}}
        if method == "GET" and route == "/item":
            i = str(query.get("id", ""))
            r = store.get_many([i])[0] if ID_RE.fullmatch(i) else None
            return (200, {"ok": True, "record": r}) if r else (404, {"ok": False, "error": "Not found."})
        if method == "GET" and route == "/export":
            out = []
            for r in store.get_many(store.ids(2000)):
                if r and r["trainer"]:
                    out.append({"id": r["id"], "target": r["target"], "rubric_version": r["rubric_version"], "text": r["text"],
                                "rules": {k: v["rules"] for k, v in r["categories"].items()},
                                "judge": {k: v["judge"] for k, v in r["categories"].items()},
                                "final": {k: v["final"] for k, v in r["categories"].items()},
                                "trainer": r["trainer"]})
            return 200, {"ok": True, "count": len(out), "records": out}
        if method == "POST" and route == "/correct":
            i = str(body.get("id", ""))
            r = store.get_many([i])[0] if ID_RE.fullmatch(i) else None
            if not r:
                return 404, {"ok": False, "error": "Not found."}
            scores = {}
            for k, c in r["categories"].items():
                try:
                    v = float(body["scores"][k])
                except Exception:
                    return 400, {"ok": False, "error": f"Enter a number for {k}."}
                if not 0 <= v <= c["max"]:
                    return 400, {"ok": False, "error": f"{k} must be between 0 and {c['max']}."}
                scores[k] = round(v, 1)
            r["trainer"] = {"scores": scores, "score": _total(scores, r["categories"]), "note": str(body.get("note", ""))[:500],
                            "at": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
            store.update(r)
            return 200, {"ok": True, "trainer": r["trainer"]}
        if method == "POST" and route == "/delete":
            i = str(body.get("id", ""))
            if not ID_RE.fullmatch(i):
                return 404, {"ok": False, "error": "Not found."}
            store.delete(i)
            return 200, {"ok": True}
        return 404, {"ok": False, "error": "Unknown action."}
    except Exception:
        return 500, {"ok": False, "error": "Something went wrong. Try again."}
