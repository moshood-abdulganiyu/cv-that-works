"""Step 8 part 2: the new routes in app.py. No network. Run: python -m tests.test_routes"""
import io
import json
import os

import app as webapp
from core import review
from core.review import MemoryReviewStore, save_for_review

for k in ("KV_REST_API_URL", "KV_REST_API_TOKEN", "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"):
    os.environ.pop(k, None)
os.environ["REVIEW_TOKEN"] = "a-long-secret-code"
ms = MemoryReviewStore()
review.get_review_store = webapp.get_review_store = lambda: ms
rep = {"rubric_version": "v", "blend_version": "b", "mode": "blended", "target": "internship", "score": 50, "band": "Needs work",
       "less_certain": ["bullets"], "categories": {"bullets": {"key": "bullets", "max": 20, "points": 10}}, "judge": {"ok": False, "reason": "off"}}
save_for_review(rep, "Led a team of 12.", ms)


def call(method, path, token=None, body=None, qs=""):
    raw = json.dumps(body).encode() if body is not None else b""
    env = {"PATH_INFO": path, "REQUEST_METHOD": method, "QUERY_STRING": qs, "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
    if token:
        env["HTTP_X_REVIEW_TOKEN"] = token
    out = {}
    res = webapp.app(env, lambda status, headers: out.update(status=int(status.split()[0]), headers=dict(headers)))
    return out["status"], b"".join(res), out["headers"]


st, b, _ = call("GET", "/api/review/list")
assert st == 401
st, b, _ = call("GET", "/api/review/list", "a-long-secret-code")
rows = json.loads(b)["rows"]
assert st == 200 and len(rows) == 1 and rows[0]["flagged"]
st, b, _ = call("GET", "/api/review/item", "a-long-secret-code", qs="id=" + rows[0]["id"])
assert st == 200 and json.loads(b)["record"]["text"] == "Led a team of 12."
st, b, _ = call("POST", "/api/review/correct", "a-long-secret-code", {"id": rows[0]["id"], "scores": {"bullets": 12}})
assert st == 200 and json.loads(b)["trainer"]["score"] == 60
st, b, _ = call("POST", "/api/review/delete", "a-long-secret-code", {"id": rows[0]["id"]})
assert st == 200
assert call("PUT", "/api/review/list", "a-long-secret-code")[0] == 404
st, b, h = call("GET", "/review")
assert st == 200 and b"trainer review" in b and h["Cache-Control"] == "no-store" and "noindex" in h["X-Robots-Tag"]
st, b, _ = call("GET", "/api/health")
hd = json.loads(b)
assert hd["review_code_set"] is True and hd["review_database"] is True
assert call("GET", "/")[0] == 200
print("ok: review routes, review page, health flags and the main page all respond")
