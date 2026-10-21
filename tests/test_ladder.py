"""Step 3 calibration tests. Run: python -m tests.test_ladder"""
from core.engine import score_text
from tests.ladder import rungs


def scores(target="internship"):
    return {n: score_text(t, 1, target) for n, t in rungs().items()}


def test_order_is_strictly_right():
    vals = [r["score"] for r in scores().values()]
    assert all(a > b for a, b in zip(vals, vals[1:])), vals


def test_anchors():
    r = scores()
    assert 90 <= r["R8 strong"]["score"] <= 100 and r["R8 strong"]["band"] == "Ready"
    assert 30 <= r["R1 weak fictional"]["score"] <= 45 and r["R1 weak fictional"]["band"] == "Rebuild"
    assert 35 <= r["R2 no projects, leadership or phone"]["score"] <= 45


def test_every_band_appears():
    assert {r["band"] for r in scores().values()} == {"Ready", "Nearly", "Needs work", "Rebuild"}


def test_repeat_runs_identical():
    a, b = scores(), scores()
    assert {k: v["score"] for k, v in a.items()} == {k: v["score"] for k, v in b.items()}


def test_planted_flaws_are_named():
    r = scores()
    assert any("email" in f["text"].lower() for f in r["R7 casual email, no LinkedIn"]["all_fixes"])
    assert any("linkedin" in f["text"].lower() for f in r["R7 casual email, no LinkedIn"]["all_fixes"])
    assert any("cliché" in f["text"].lower() for f in r["R5 cliché summary"]["all_fixes"])
    assert any("weak phrase" in f["text"].lower() for f in r["R4 weak phrases, thin extras"]["all_fixes"])
    assert r["R3 no numbers"]["categories"]["evidence"]["points"] == 0
    assert any("Projects" in m for m in r["R2 no projects, leadership or phone"]["missing_sections"])


def test_placeholder_notice():
    r = score_text(open("tests/samples/strong_fictional.txt").read().replace("1st place", "[__] place"), 1, "internship")
    assert any("placeholder" in n for n in r["notices"])


if __name__ == "__main__":
    for n, fn in list(globals().items()):
        if n.startswith("test_"):
            fn(); print("ok", n)
    for n, r in scores().items():
        print(f"{n:<38}{r['score']:>4}  {r['band']}")
