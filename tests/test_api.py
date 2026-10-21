"""Step 4 tests. Runs the real handler on localhost, no Vercel needed.  python -m tests.test_api"""
import io
import json
import os
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

os.environ["UPLOADS_PER_DEVICE_PER_DAY"] = "3"
os.environ["UPLOADS_PER_IP_PER_DAY"] = "50"
os.environ.pop("KV_REST_API_URL", None); os.environ.pop("UPSTASH_REDIS_REST_URL", None)

from api.score import handler                      # noqa: E402
from core.service import _scrub, public_report     # noqa: E402

SAMPLES = Path(__file__).parent / "samples"


def make_docx(text):
    import docx
    d = docx.Document()
    for line in text.splitlines():
        d.add_paragraph(line)
    buf = io.BytesIO(); d.save(buf)
    return buf.getvalue()


def multipart(fields, file=None):
    b = "----cvtwboundary"
    out = b""
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    if file:
        name, data = file
        out += f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + data + b"\r\n"
    return out + f"--{b}--\r\n".encode(), f"multipart/form-data; boundary={b}"


def post(port, fields, file=None, cookie=None):
    body, ctype = multipart(fields, file)
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/score", data=body, headers={"Content-Type": ctype, **({"Cookie": cookie} if cookie else {})})
    try:
        r = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        r = e
    return r.status, json.loads(r.read()), r.headers.get("Set-Cookie")


def main():
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_port
    cv = make_docx((SAMPLES / "strong_fictional.txt").read_text())
    ok = {"consent": "true", "target": "internship"}

    s, p, c1 = post(port, ok, ("cv.docx", cv))
    assert s == 200 and p["ok"] and p["result"]["band"] and p["stored"] is False, p
    assert "facts" not in p["result"], "facts must not reach the browser"
    dumped = json.dumps(p)
    assert "@" not in dumped.replace("[email]", ""), "email leaked"
    cookie = c1.split(";")[0]
    assert p["uploads_left_today"] == 2
    print("ok  scores a DOCX, no facts in response, cookie set, 2 uploads left")

    s, p, _ = post(port, {"target": "internship"}, ("cv.docx", cv), cookie)
    assert s == 400 and p["error"]["code"] == "missing_consent"
    s, p, _ = post(port, ok, None, cookie)
    assert s == 400 and p["error"]["code"] == "no_file"
    s, p, _ = post(port, ok, ("cv.txt", b"hello " * 50), cookie)
    assert s == 422 and p["error"]["code"] == "unsupported_type", p
    s, p, _ = post(port, ok, ("cv.pdf", b""), cookie)
    assert s == 400 and p["error"]["code"] == "no_file"
    s, p, _ = post(port, ok, ("cv.pdf", b"not a real pdf at all" * 20), cookie)
    assert s == 422 and p["error"]["code"] in ("corrupt", "empty_file"), p
    print("ok  missing consent, no file, wrong type, corrupt file give clear errors")

    s, p, _ = post(port, ok, ("big.pdf", b"x" * (4 * 1024 * 1024 + 200_000)), cookie)
    assert s == 413 and p["error"]["code"] == "too_large", p
    print("ok  oversized upload refused with 413")

    s, p, _ = post(port, {"consent": "true", "target": "not sure"}, ("cv.docx", cv), cookie)
    assert s == 200 and p["result"]["target"] == "none" and p["uploads_left_today"] == 1, p
    s, p, _ = post(port, ok, ("cv.docx", cv), cookie)
    assert s == 200 and p["uploads_left_today"] == 0
    s, p, _ = post(port, ok, ("cv.docx", cv), cookie)
    assert s == 429 and p["error"]["code"] == "limit_reached", p
    print("ok  failed reads did not use up uploads; 4th upload blocked with limit_reached; 'not sure' drops Fit")

    s, p, _ = post(port, ok, ("cv.docx", cv))     # new device cookie, same IP
    assert s == 200
    print("ok  a new device on the same IP is counted separately (IP cap is higher)")

    r = {"facts": {"email": "a@b.com"}, "rewrites": [{"original": "Mail me ada.o@gmail.com or 0803 123 4567, ran 2023 - 2024 drive for 12,000 people"}]}
    pr = public_report(r)
    assert "facts" not in pr
    t = pr["rewrites"][0]["original"]
    assert "[email]" in t and "[phone]" in t and "2023 - 2024" in t and "12,000" in t, t
    print("ok  scrub hides emails and phones, keeps years and counts")
    srv.shutdown()
    print("\nAll step 4 tests passed.")


if __name__ == "__main__":
    main()
