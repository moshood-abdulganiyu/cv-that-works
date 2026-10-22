"""Step 8: blend the rules score and the AI judge score into one result per category.
Rules lead on facts, the judge leads on judged items. Input is a finished rules report that already has report["judge"].
Never raises: on any problem the caller keeps the rules-only report."""
import copy

from .rubric import BANDS, MAX_POINTS

BLEND_VERSION = "blend-v1.0"
GAP = 0.30                       # voters differing by more than 30% of a category's points = "less certain"
JUDGED = ("evidence", "bullets", "summary", "language", "fit")


def _band(total):
    return next(name for floor, name in BANDS if total >= floor)


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def blend_category(cat, j):
    """Return (blended_points, voters_differ). j is the judge's whole-number score or None."""
    mode, mx = cat["judge_mode"], cat["max"]
    if j is None or mode == "none":
        return cat["points"], False
    rules = cat["rules_points"]
    if mode == "range":                       # evidence: judge decides inside the band the rules set
        pts = _clamp(j, cat["range_low"], cat["range_high"])
        return pts, abs(j - cat["points"]) > GAP * mx
    if mode == "full":                        # bullets, summary, fit: two voters, so the average
        j = _clamp(j, 0, mx)
        return (rules + j) / 2, abs(j - rules) > GAP * mx
    if mode == "part":                        # language: rules part plus the judge's typo and voice score
        if cat["key"] != "language":
            return cat["points"], False
        jm = cat.get("judged_max", 5)
        return rules + _clamp(j, 0, jm), False   # the gap can never pass 30% here, so no flag
    return cat["points"], False


def blend_report(report):
    r = copy.deepcopy(report)
    jd = r.get("judge") or {}
    if not jd.get("ok"):
        return r
    scores = jd.get("scores") or {}
    less, detail = [], {}
    for k, cat in r["categories"].items():
        j = scores.get(k)
        j = None if j is None else float(j)
        before = cat["points"]
        pts, differ = blend_category(cat, j)
        cat["rules_total"] = before
        cat["judge_points"] = j
        cat["points"] = round(pts, 1)
        cat["blended"] = j is not None and cat["judge_mode"] != "none"
        cat["less_certain"] = bool(differ)
        if differ:
            less.append(k)
            detail[k] = {"rules": before if cat["judge_mode"] == "range" else cat["rules_points"], "judge": j}
    use = list(r["categories"])
    raw = sum(r["categories"][k]["points"] for k in use)
    total = round(raw * 100 / sum(MAX_POINTS[k] for k in use))
    r["score"], r["band"] = total, _band(total)
    r["less_certain"] = less
    r["review"] = {"needed": bool(less), "categories": less, "detail": detail}
    r["mode"] = "blended"
    r["blend_version"] = BLEND_VERSION
    _regain(r)
    _notices(r, less)
    return r


def _regain(r):
    """Keep fix gains honest: a category's fixes can never add more than the room left under its blended points."""
    scale = 100 / 95 if r["target"] == "none" else 1.0
    fixes = r.get("all_fixes", [])
    per = {}
    for x in fixes:
        per[x["category"]] = per.get(x["category"], 0) + x["gain"]
    for x in fixes:
        c = r["categories"].get(x["category"])
        if not c:
            continue
        room = max(0.0, (c["max"] - c["points"]) * scale)
        if per[x["category"]] > room:
            x["gain"] = round(x["gain"] * room / per[x["category"]], 1)
    fixes = [x for x in fixes if x["gain"] > 0.05]
    order = {k: i for i, k in enumerate(MAX_POINTS)}
    fixes.sort(key=lambda x: (-x["gain"], order[x["category"]]))
    r["all_fixes"], r["fixes"] = fixes, fixes[:3]
    if r["band"] != "Rebuild" and fixes:
        r["next_step"] = f"Make fix 1 ({fixes[0]['text'].split('.')[0]}), then upload again to see your new score."
    elif r["band"] != "Rebuild":
        r["next_step"] = "Tailor this CV to each opportunity you apply for."


def _notices(r, less):
    keep = [n for n in r.get("notices", []) if not n.startswith("Checked by rules only")]
    keep.insert(0, "Scored by two readers together: a rules check and an AI reader.")
    if less:
        names = ", ".join(r["categories"][k]["label"] for k in less)
        keep.append(f"Less certain: the two readers saw {names} differently. Treat those points as a guide, not a verdict.")
    r["notices"] = keep
