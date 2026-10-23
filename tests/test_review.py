"""Step 8 part 2 tests: save tickbox, review store, trainer endpoints. No network.
Run: python -m tests.test_review"""
import json
import os
from core import service
from core.review import MemoryReviewStore, build_record, handle_review, save_for_review

for k in ("KV_REST_API_URL", "KV_REST_API_TOKEN", "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN", "REVIEW_TOKEN"):
    os.environ.pop(k, None)

TEXT = "[name]\nLagos | [email] | [phone]\nLed a team of 12 volunteers. Contact someone@mail.com"


def report(flagged=False):
    cats = {"evidence": {"key": "evidence", "max": 20, "points": 9, "rules_total": 8, "judge_points": 14.0, "less_certain": False},
            "bullets": {"key": "bullets", "max": 20, "points": 14.5, "rules_total": 10, "judge_points": 19.0, "less_certain": flagged}}
    return {"rubric_version": "cv-rubric-v1.0", "blend_version": "blend-v1.0", "mode": "blended", "target": "internship",
            "score": 58, "band": "Needs work", "less_certain": ["bullets"] if flagged else [], "categories": cats,
            "judge": {"ok": True, "scores": {"evidence": 14, "bullets": 19}, "strengths": [], "fixes": [], "rewrites": []},
            "facts": {"email": "secret@x.com"}, "notices": [], "_saved_text": TEXT}


# 1. record content
rec = build_record(report(True), TEXT)
assert "someone@mail.com" not in rec["text"] and "[email]" in rec["text"]
assert rec["categories"]["evidence"]["rules"] == 8 and rec["categories"]["evidence"]["judge"] == 14.0
assert rec["trainer"] is None and len(rec["id"]) == 16 and "facts" not in rec and "secret@x.com" not in json.dumps(rec)

# 2. saving
ms = MemoryReviewStore()
assert save_for_review(report(), TEXT, ms) is True
assert save_for_review(report(), TEXT, None) is False          # no database connected: nothing claimed as saved
assert save_for_review(report(), "   ", ms) is False
assert len(ms.ids_) == 1 and not ms.flag


# 3. the service: second tickbox
def multipart(fields, with_file=True):
    b = "XBOUND"
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items()]
    if with_file:
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="cv.pdf"\r\nContent-Type: application/pdf\r\n\r\nPDFDATA\r\n')
    body = ("".join(parts) + f"--{b}--\r\n").encode()
    return f"multipart/form-data; boundary={b}", body


def call(fields, review_store):
    ct, body = multipart(fields)
    return service.handle_score(ct, len(body), lambda n: body, "", "1.2.3.4", store=service.MemoryStore(), review_store=review_store)


service.score_file = lambda name, data, target, judge=False, keep_text=False: report(True)
ms = MemoryReviewStore()
st, p, _ = call({"consent": "true", "target": "internship"}, ms)                  # save box not ticked
assert st == 200 and p["stored"] is False and not ms.ids_
st, p, _ = call({"consent": "true", "target": "internship", "save": "on"}, ms)    # ticked
assert st == 200 and p["stored"] is True and len(ms.ids_) == 1 and ms.flag == set(ms.ids_)
assert any(n.startswith("Saved for the trainer") for n in p["result"]["notices"])
assert "_saved_text" not in json.dumps(p) and "Lagos" not in json.dumps(p) and "facts" not in p["result"]
st, p, _ = call({"consent": "true", "target": "internship", "save": "on"}, None)  # no database
assert st == 200 and p["stored"] is False and "score" in p["result"]
st, p, _ = call({"save": "on"}, ms)                                               # save without consent is refused
assert st == 400 and p["error"]["code"] == "missing_consent" and len(ms.ids_) == 1

# 4. trainer endpoints
ms = MemoryReviewStore()
save_for_review(report(False), TEXT, ms)
save_for_review(report(True), TEXT, ms)
ok_id, flag_id = ms.ids_[1], ms.ids_[0]
assert handle_review("GET", "/api/review/list", "x", store=ms)[0] == 503             # no REVIEW_TOKEN set yet
os.environ["REVIEW_TOKEN"] = "a-long-secret-code"
assert handle_review("GET", "/api/review/list", "wrong", store=ms)[0] == 401
assert handle_review("GET", "/api/review/list", None, store=ms)[0] == 401
tok = "a-long-secret-code"
st, p = handle_review("GET", "/api/review/list", tok, store=ms)
assert st == 200 and p["rows"][0]["id"] == flag_id and p["rows"][0]["flagged"] and p["counts"] == {"saved": 2, "waiting": 1, "corrected": 0}
assert "text" not in p["rows"][0]
st, p = handle_review("GET", "/api/review/item", tok, query={"id": flag_id}, store=ms)
assert st == 200 and p["record"]["text"].startswith("[name]")
assert handle_review("GET", "/api/review/item", tok, query={"id": "../etc"}, store=ms)[0] == 404
assert handle_review("POST", "/api/review/correct", tok, {"id": flag_id, "scores": {"evidence": 30, "bullets": 10}}, store=ms)[0] == 400
assert handle_review("POST", "/api/review/correct", tok, {"id": flag_id, "scores": {"evidence": 10}}, store=ms)[0] == 400
st, p = handle_review("POST", "/api/review/correct", tok, {"id": flag_id, "scores": {"evidence": 10, "bullets": 12}, "note": "ok"}, store=ms)
assert st == 200 and p["trainer"]["score"] == round(22 * 100 / 40) and flag_id not in ms.flag
st, p = handle_review("GET", "/api/review/export", tok, store=ms)
assert p["count"] == 1 and p["records"][0]["trainer"]["scores"]["bullets"] == 12 and p["records"][0]["rules"]["bullets"] == 10
assert handle_review("POST", "/api/review/delete", tok, {"id": flag_id}, store=ms)[0] == 200
assert handle_review("GET", "/api/review/list", tok, store=ms)[1]["counts"]["saved"] == 1
print("ok: save box, redacted-only storage, trainer list, correction, export and delete all behave")
