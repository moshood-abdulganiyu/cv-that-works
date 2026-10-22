"""Run: python -m tests.test_blend"""
from core.blend import blend_report
from core.rubric import MAX_POINTS


def cat(key, pts, jm, rp=None, fb=0.0, **x):
    rp = pts if rp is None else rp
    return {"key": key, "label": key, "max": MAX_POINTS[key], "judge_mode": jm, "rules_points": rp,
            "fallback_points": fb, "points": rp + fb, "items": [], **x}


def base(target="internship"):
    cs = {"evidence": cat("evidence", 8, "range", range_low=5, range_high=9),
          "bullets": cat("bullets", 10, "full"), "sections": cat("sections", 12, "none"),
          "summary": cat("summary", 6, "full"), "contact": cat("contact", 8, "none"),
          "language": cat("language", 4, "part", rp=4, fb=3.0, judged_max=5),
          "format": cat("format", 8, "part", rp=6, fb=2.0, judged_max=2), "fit": cat("fit", 3, "full")}
    if target == "none":
        cs.pop("fit")
    return {"target": target, "categories": cs, "score": 0, "band": "", "mode": "rules_with_ai_comments", "less_certain": [],
            "notices": ["Checked by rules only. The AI check was not used for this result."],
            "all_fixes": [{"category": "bullets", "text": "Fix bullets. More.", "gain": 6.0},
                          {"category": "evidence", "text": "Add numbers. More.", "gain": 5.0},
                          {"category": "sections", "text": "Add Awards. More.", "gain": 1.0}], "fixes": [], "next_step": "",
            "judge": {"ok": True, "scores": {"evidence": 14, "bullets": 12, "summary": 6, "language": 4, "fit": 4}}}


r = blend_report(base())
c = r["categories"]
assert c["evidence"]["points"] == 9, c["evidence"]          # 14 clamped into 5 to 9
assert c["bullets"]["points"] == 11                         # (10+12)/2
assert c["language"]["points"] == 8                         # 4 + 4, not 4 + 3
assert c["format"]["points"] == 8 and c["sections"]["points"] == 12   # rules only
assert r["less_certain"] == [] and r["mode"] == "blended"
assert not any(n.startswith("Checked by rules only") for n in r["notices"])

b = base(); b["judge"]["scores"]["bullets"] = 19            # rules 10 vs judge 19: gap 9 > 6
r = blend_report(b)
assert r["less_certain"] == ["bullets"] and r["review"]["needed"]
assert r["categories"]["bullets"]["points"] == 14.5

b = base(); b["judge"]["scores"]["evidence"] = 0            # judge far below rules range: clamp up, flag
r = blend_report(b)
assert r["categories"]["evidence"]["points"] == 5 and "evidence" in r["less_certain"]

b = base("none"); b["judge"]["scores"]["fit"] = None
r = blend_report(b)
assert "fit" not in r["categories"]
assert r["score"] == round(sum(x["points"] for x in r["categories"].values()) * 100 / 95)

b = base(); b["judge"]["scores"]["bullets"] = 20            # bullets ends at 15, room 5, fix said 6
r = blend_report(b)
assert r["all_fixes"][0]["gain"] <= 5.0 and all(x["gain"] <= 20 for x in r["all_fixes"])

b = base(); b["judge"] = {"ok": False, "reason": "rate_limited"}   # fallback keeps the report untouched
r = blend_report(b)
assert r["mode"] == "rules_with_ai_comments" and r["categories"]["bullets"]["points"] == 10
print("blend tests passed")
