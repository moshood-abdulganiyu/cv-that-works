"""Smoke tests for step 2. Full calibration ladder comes in step 3. Run: python -m tests.test_smoke"""
import io
from pathlib import Path

from core.engine import score_file, score_text
from core.reader import CVReadError, read_document
from core.rubric import RUBRIC_VERSION

S = Path(__file__).parent / "samples"


def load(name):
    return (S / name).read_text(encoding="utf-8")


def test_weak_vs_strong_order():
    weak, strong = score_text(load("weak_fictional.txt"), 1, "internship"), score_text(load("strong_fictional.txt"), 1, "internship")
    assert weak["score"] < 50 and weak["band"] == "Rebuild", weak["score"]
    assert strong["score"] >= 85 and strong["band"] == "Ready", strong["score"]
    assert strong["score"] - weak["score"] >= 40


def test_version_and_shape():
    r = score_text(load("strong_fictional.txt"), 1, "internship")
    assert r["rubric_version"] == RUBRIC_VERSION and r["mode"] == "rules_only"
    assert set(r["categories"]) == {"evidence", "bullets", "sections", "summary", "contact", "language", "format", "fit"}
    assert len(r["fixes"]) <= 3 and r["defend_line"] and r["less_certain"] == []


def test_no_target_rescales_and_drops_fit():
    r = score_text(load("strong_fictional.txt"), 1, None)
    assert "fit" not in r["categories"] and r["target"] == "none" and 0 <= r["score"] <= 100
    r2 = score_text(load("strong_fictional.txt"), 1, "not sure")
    assert "fit" not in r2["categories"]


def test_weak_flags_and_rewrites():
    r = score_text(load("weak_fictional.txt"), 1, "internship")
    assert any("prototype" in f["question"].lower() for f in r["flags"])
    assert r["rewrites"] and all("[__" in w["rewrite"] for w in r["rewrites"])
    assert not any(ch.isdigit() for w in r["rewrites"] for ch in w["rewrite"])   # never invents a number


def test_short_cv_not_crushed():
    short = ("Sample Student Three\nLagos | sample.three@gmail.com | 08031234567 | linkedin.com/in/sample-three\n\nSummary\nSecond-year student seeking a first internship. "
             "Led a team of 5 to win a campus debate.\n\nEducation\nUniversity of Sample, B.Sc. Economics, 2024 - 2028\n\nProjects\n"
             "- Built a budget tracker in Excel used by 12 classmates\n- Led a team of 5 in a debate that won 1st place among 8 teams\n"
             "\nLeadership and Volunteering\n- Organised a clean-up of 1 street with 15 volunteers\n- Taught 10 pupils basic reading over 4 weeks\n\nSkills\nExcel, Public speaking\n")
    r = score_text(short, 1, "internship")
    assert r["score"] >= 70, r["score"]
    assert r["short_cv_note"]


def test_pdf_docx_and_errors():
    from reportlab.pdfgen import canvas
    import docx
    text = load("strong_fictional.txt")
    buf = io.BytesIO(); c = canvas.Canvas(buf); y = 800
    for line in text.splitlines():
        c.setFont("Helvetica", 9); c.drawString(40, y, line[:110]); y -= 13
    c.save()
    r = score_file("cv.pdf", buf.getvalue(), "internship")
    assert r["facts"]["pages"] == 1 and r["score"] >= 70, r["score"]
    d = docx.Document()
    for line in text.splitlines():
        d.add_paragraph(line)
    out = io.BytesIO(); d.save(out)
    assert score_file("cv.docx", out.getvalue(), "internship")["score"] >= 70
    blank = io.BytesIO(); c = canvas.Canvas(blank); c.rect(50, 50, 100, 100); c.save()      # a page with no text layer, like a scan
    for name, data, code in [("scan.pdf", blank.getvalue(), "scanned_pdf"), ("cv.doc", b"abc", "unsupported_type"),
                             ("cv.pdf", b"", "empty_file"), ("cv.pdf", b"not a pdf", "corrupt"), ("big.pdf", b"0" * (5 * 1024 * 1024), "too_large")]:
        try:
            read_document(name, data); raise AssertionError(f"{name} should fail")
        except CVReadError as e:
            assert e.code == code, (name, e.code)


if __name__ == "__main__":
    for n, fn in list(globals().items()):
        if n.startswith("test_"):
            fn(); print("ok", n)
