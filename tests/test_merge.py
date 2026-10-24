"""Merged advice: one fix list and one set of rewrites, scores untouched, fallback intact."""
import copy
import json

from core import blend, judge
from core.checker import check_cv
from core.rules import score_rules

CV = """Ada Obi
Lagos, Nigeria | ada.obi@gmail.com
SUMMARY
Hardworking student seeking opportunities.
EXPERIENCE
Student Intern - Machine Learning
Jun - Dec 2024
\u2022 Responsible for helping with data cleaning for the team
\u2022 Built a dashboard that cut reporting time by 40% for the department
\u2022 Worked on outreach for pupils
PROJECTS
Leaf Disease Classifier
2025 - Present
\u2022 Achieved 90% accuracy on a held-out test set of 2,152 leaf images
SKILLS
Python, Excel
"""


def make(with_category=True):
    facts = check_cv(CV, 1)
    rep = score_rules(facts, "internship")
    fixes = [{"text": "Name the data you cleaned and how many rows, using [__] if unsure."},
             {"text": "Add a goal and one proof point to your summary."}]
    if with_category:
        fixes[0]["category"], fixes[1]["category"] = "bullets", "summary"
    ans = {"scores": {"evidence": 12, "bullets": 8, "summary": 3, "language": 4, "fit": 3}, "reasons": {},
           "strengths": [{"title": "Clear numbers", "reason": "40% is a clear result."}], "fixes": fixes,
           "rewrites": [{"bullet_number": 1, "rewrite": "Cleaned data for the team, [__ how many records].", "note": "Names what you did."}]}
    out = judge.validate(json.dumps(ans), facts, [b[:300] for b in facts["bullets"]], "internship")
    out.update(ok=True, model="test")
    judge.attach_judge(rep, out)
    return rep


def test_scores_do_not_change():
    a, b = blend.blend_report(make(True)), blend.blend_report(make(False))
    assert a["score"] == b["score"] and a["band"] == b["band"]
    assert {k: c["points"] for k, c in a["categories"].items()} == {k: c["points"] for k, c in b["categories"].items()}


def test_ai_fixes_replace_rules_fixes_in_their_categories():
    r = blend.blend_report(make(True))
    texts = [x["text"] for x in r["all_fixes"]]
    assert any("Name the data you cleaned" in t for t in texts) and any("goal and one proof point" in t for t in texts)
    assert not any("weak phrases" in t for t in texts), "old rules bullet advice should be gone"
    assert all(x["gain"] > 0 for x in r["fixes"]) and len(r["fixes"]) <= 3
    assert r["fixes"][0]["text"].split(".")[0] in r["next_step"]


def test_no_category_means_rules_advice_stays():
    plain = make(False)
    rules_texts = [x["text"] for x in plain["all_fixes"]]
    r = blend.blend_report(plain)
    assert any("weak phrases" in x["text"] for x in r["all_fixes"])
    assert not any(x.get("source") == "ai" for x in r["all_fixes"])


def test_ai_rewrites_used_and_notice_cleaned():
    r = blend.blend_report(make(True))
    assert r["rewrites"][0]["rewrite"].startswith("Cleaned data")
    assert not any(n.startswith("Your score comes from the rules checks") for n in r["notices"])
    assert r["notices"][0].startswith("Scored by two readers")


def test_judge_failure_keeps_rules_report():
    rep = make(True)
    rep["judge"] = {"ok": False, "reason": "rate_limited"}
    before = copy.deepcopy(rep)
    assert blend.blend_report(rep) == before


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
