"""Step 7 tests: redaction, the AI judge with a fake Gemini, and the fallbacks. No network, no real key.
Run: python -m tests.test_judge"""
import json
from core import judge
from core.engine import score_text
from core.redact import redact_text

CV = """Jane Example
Lagos, Nigeria | jane.example@gmail.com | +234 800 000 0000 | https://www.linkedin.com/in/jane-example | @janeex
12 Adeniyi Street, Ikeja
SUMMARY
200-level Biology student seeking a research internship, who led a 15-person health outreach for 120 pupils.
EDUCATION
University of Example, B.Sc. Biology, 200 Level
LEADERSHIP & VOLUNTEERING
Project Lead June 2026
Example Club Lagos, Nigeria
Led a team of 12 volunteers to teach first aid to 60 students.
Raised 40,000 naira for school supplies in two weeks.
Organised a career talk for undergraduates which students enjoyed.
Helped with the club newsletter for the whole department each month.
SKILLS
Research writing, public speaking
"""
ENV = {"GEMINI_API_KEY": "fake", "GEMINI_MODEL": "m-main", "GEMINI_MODEL_BACKUP": "m-backup"}
GOOD = {"scores": {"evidence": 14, "bullets": 99, "summary": 8, "language": 4, "fit": 3},
        "reasons": {"bullets": "Most bullets start with a verb \u2014 good."},
        "strengths": [{"title": "Clear scale", "reason": "Numbers show size."}] * 3,
        "fixes": [{"text": "Add a result to the newsletter bullet."}] * 3,
        "rewrites": [{"bullet_number": 3, "rewrite": "Organised a career talk for [__ how many] undergraduates, which [__ result].", "note": ""},
                     {"bullet_number": 4, "rewrite": "Wrote 4 newsletters, reaching 500 readers.", "note": ""}]}


def fake(*answers):
    calls = []
    def _call(model, system, user, key, timeout):
        calls.append((model, user))
        a = answers[min(len(calls) - 1, len(answers) - 1)]
        if isinstance(a, judge.JudgeError):
            raise a
        return a if isinstance(a, str) else json.dumps(a)
    return _call, calls


def facts_for(text):
    from core.checker import check_cv
    return check_cv(text, 1)


def run():
    # 1. redaction
    f = facts_for(CV)
    out = redact_text(CV, f["name_line"])
    for bad in ("jane.example@gmail.com", "+234 800", "linkedin.com", "@janeex", "Adeniyi", "Jane"):
        assert bad not in out, bad
    assert "40,000" in out and "2026" in out and "120 pupils" in out
    assert "[name]" in out and "[email]" in out and "[phone]" in out
    # 2. nothing personal is sent to the AI
    call, calls = fake(GOOD); judge.CALLER = call; judge._cooldown.clear()
    j = judge.judge_cv(f, "internship", ENV)
    assert j["ok"] and j["model"] == "m-main"
    sent = calls[0][1]
    for bad in ("jane.example", "+234", "linkedin", "Adeniyi", "Jane"):
        assert bad not in sent, bad
    # 3. checks on the answer: scores clamped, em dash removed, invented numbers refused
    assert j["scores"]["bullets"] == 20 and "\u2014" not in json.dumps(j)
    assert len(j["rewrites"]) == 1 and j["rewrites"][0]["original"].startswith("Organised")
    # 4. no target means no fit score
    assert judge.judge_cv(f, None, ENV)["scores"]["fit"] is None
    # 5. main model rate limited: backup used, and the main model rests for a minute
    judge._cooldown.clear()
    call, calls = fake(judge.JudgeError("rate_limited"), GOOD); judge.CALLER = call
    j = judge.judge_cv(f, None, ENV)
    assert j["ok"] and j["model"] == "m-backup" and [c[0] for c in calls] == ["m-main", "m-backup"]
    call, calls = fake(GOOD); judge.CALLER = call
    assert judge.judge_cv(f, None, ENV)["model"] == "m-backup" and [c[0] for c in calls] == ["m-backup"]
    # 6. both fail, bad JSON, no key, switched off: never raises, always a rules result
    for answers in ((judge.JudgeError("rate_limited"),) * 2, ("not json at all",) * 2, (judge.JudgeError("unavailable"),) * 2):
        judge._cooldown.clear(); call, calls = fake(*answers); judge.CALLER = call
        r = score_text(CV, 1, "internship", judge=False)
        j = judge.judge_cv(f, "internship", ENV)
        assert j["ok"] is False
        r2 = judge.attach_judge(dict(r), j)
        assert r2["score"] == r["score"] and r2["judge"]["ok"] is False
    assert judge.judge_cv(f, None, {})["reason"] == "no_key"
    assert judge.judge_cv(f, None, {**ENV, "AI_JUDGE": "off"})["reason"] == "off"
    # 7. a crashing AI layer cannot break the score
    def boom(*a, **k): raise RuntimeError("x")
    judge.judge_cv, keep = boom, judge.judge_cv
    try:
        r = score_text(CV, 1, None, judge=True)
        assert r["judge"]["ok"] is False and r["score"] > 0
    finally:
        judge.judge_cv = keep
    # 8. with the AI on, the two readers are blended; the rules-only score is untouched
    judge._cooldown.clear(); call, calls = fake(GOOD); judge.CALLER = call
    import os
    os.environ.update(ENV)
    try:
        r = score_text(CV, 1, "internship", judge=True)
    finally:
        for k in ENV: os.environ.pop(k, None)
    base = score_text(CV, 1, "internship", judge=False)
    assert r["judge"]["ok"] and r["mode"] == "blended" and r["blend_version"] == "blend-v1.0"
    assert base["mode"] == "rules_only" and 0 <= r["score"] <= 100
    lang = r["categories"]["language"]
    assert abs(lang["points"] - (lang["rules_points"] + r["judge"]["scores"]["language"])) < 0.11
    assert r["categories"]["sections"]["points"] == base["categories"]["sections"]["points"]
    assert "name_line" not in r["facts"] and "skills_text" not in r["facts"]
    print("ok: redaction, judge checks, backup model and fallbacks all behave")


if __name__ == "__main__":
    run()