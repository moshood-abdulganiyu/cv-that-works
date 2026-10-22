"""Regression: a CV with no opening summary used to crash build_fixes (KeyError) and show 'Something went wrong'.
Run: python -m tests.test_no_summary"""
from core.engine import score_text

CV = """Jane Example
Lagos, Nigeria | jane.example@gmail.com | +2348000000000 | https://www.linkedin.com/in/jane-example
EDUCATION
University of Example, B.Sc. Biology, 200 Level
LEADERSHIP & VOLUNTEERING
Project Lead June 2026
Example Club Lagos, Nigeria
Led a team of 12 volunteers to teach first aid to 60 students.
Raised 40,000 naira for school supplies in two weeks.
Organised a career talk for 80 undergraduates.
SKILLS
Research writing, public speaking
"""

def run():
    for target in (None, "internship"):
        r = score_text(CV, pages=1, target=target)
        assert r["categories"]["summary"]["points"] == 0
        tips = [x["text"] for x in r["all_fixes"] if x["category"] == "summary"]
        assert any("summary" in t.lower() for t in tips), "missing summary fix"
    print("ok: CV without a summary scores and gets a summary fix")

if __name__ == "__main__":
    run()