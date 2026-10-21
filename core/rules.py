"""Rules-only scoring engine. Gives a complete score, band, fixes and templated rewrites with no AI.
Each category reports a rules part and, where an AI judge will later help, a fallback part used when it is unavailable."""
import math
import re

from .checker import BULLET_RE, has_number, is_strong_start, _first_word
from .rubric import (BANDS, LABELS, MAX_POINTS, ORDER_MAX_DEDUCTION, PAIR_POINTS, RUBRIC_VERSION, SECTION_POINTS,
                     TARGET_KEYWORDS, WEAK_PHRASES, RESULT_WORDS)

JUDGE_MODE = {"evidence": "range", "bullets": "full", "summary": "full", "fit": "full",
              "language": "part", "format": "part", "sections": "none", "contact": "none"}
SECTION_NAMES = {"education": "Education", "projects": "Projects", "skills": "Skills", "awards": "Awards",
                 "memberships": "Professional memberships and associations", "certifications": "Certifications and training"}
EVIDENCE_STEPS = [0.15, 0.40, 0.70]


def band_for(total):
    return next(name for floor, name in BANDS if total >= floor)


def evidence_points(share):
    s = share * 100
    if s >= 70:
        return 16 + 4 * min(1, (s - 70) / 30)
    if s >= 40:
        return 10 + 5 * (s - 40) / 30
    if s >= 15:
        return 5 + 4 * (s - 15) / 25
    return 4 * s / 15


def _item(name, pts, mx, note=""):
    return {"name": name, "points": round(pts, 1), "max": mx, "note": note}


def _cat(key, items, fallback_part=0.0, **extra):
    rules = sum(i["points"] for i in items)
    c = {"key": key, "label": LABELS[key], "max": MAX_POINTS[key], "judge_mode": JUDGE_MODE[key],
         "items": items, "rules_points": round(rules, 1), "fallback_points": round(fallback_part, 1),
         "points": round(rules + fallback_part, 1)}
    c.update(extra)
    return c


# ---------- categories ----------
def score_evidence(f):
    n, share = f["bullet_total"], f["number_share"]
    pts = evidence_points(share) if n else 0.0
    note = f"{f['bullets_with_number']} of {n} bullets carry a number, scale or result" if n else "No bullets found under Experience, Projects or Leadership"
    lo, hi = (16, 20) if share >= .7 else (10, 15) if share >= .4 else (5, 9) if share >= .15 else (0, 4)
    return _cat("evidence", [_item("Bullets with a number", pts, 20, note)], range_low=lo, range_high=hi)


def score_bullets(f):
    n = f["bullet_total"]
    if not n:
        return _cat("bullets", [_item("Action-verb starts", 0, 8, "No bullets found"), _item("No weak phrases", 0, 6), _item("Scope and result", 0, 6)])
    return _cat("bullets", [
        _item("Action-verb starts", 8 * f["strong_start_share"], 8, f"{f['strong_start_count']} of {n} bullets start with an action verb"),
        _item("No weak phrases", max(0, 6 - 1.5 * f["weak_phrase_count"]), 6, f"{f['weak_phrase_count']} weak phrase(s) found"),
        _item("Scope and result", 6 * f["scope_result_share"], 6, f"{f['scope_result_count']} of {n} bullets show what you did and what came of it"),
    ])


def score_sections(f):
    items, found, cnt = [], set(f["sections_found"]), f["section_content_lines"]
    for k, pts in SECTION_POINTS.items():
        if k in found and cnt.get(k, 0) >= 1:
            items.append(_item(SECTION_NAMES[k], pts, pts, "found"))
        elif k in found:
            items.append(_item(SECTION_NAMES[k], pts / 2, pts, "heading found but nothing under it"))
        else:
            items.append(_item(SECTION_NAMES[k], 0, pts, "not found"))
    best = max(cnt.get("experience", 0), cnt.get("leadership", 0))
    has_head = "experience" in found or "leadership" in found
    pair = PAIR_POINTS if best >= 2 else PAIR_POINTS / 2 if (best >= 1 or has_head) else 0
    items.append(_item("Experience or Leadership/volunteering", pair, PAIR_POINTS,
                       "strong" if pair == PAIR_POINTS else "thin" if pair else "neither found"))
    idx = f["section_line_index"]
    ded, why = 0.0, []
    if not f["contact_in_top"] and (f["email"] or f["phone"]):
        ded += 1; why.append("contact details are not at the top")
    if "summary" in idx and any(k in idx and idx[k] < idx["summary"] for k in ("education", "projects", "experience")):
        ded += 0.5; why.append("summary should come right after contact details")
    for k in ("education", "projects"):
        if "experience" in idx and k in idx and idx["experience"] < idx[k]:
            ded += 0.25; why.append(f"{SECTION_NAMES[k]} should sit above Experience for a student")
    ded = min(ded, ORDER_MAX_DEDUCTION)
    if ded:
        items.append(_item("Order of sections", -ded, 0, "; ".join(why)))
    c = _cat("sections", items)
    c["rules_points"] = c["points"] = round(max(0, c["rules_points"]), 1)
    c["language_note"] = "Languages heading found, a nice extra" if "languages" in found else ""
    return c


def score_summary(f):
    if not f["summary_present"]:
        return _cat("summary", [_item("Summary present", 0, 4, "no opening summary found"), _item("Right length", 0, 2),
                                _item("Names your goal", 0, 2), _item("One proof point", 0, 2)])
    note = "" if f["summary_headed"] else " (add a heading called Summary)"
    return _cat("summary", [
        _item("Summary present", 4, 4, "found" + note),
        _item("Right length (2 to 3 lines)", 2 if f["summary_length_ok"] else 0, 2, f"{f['summary_words']} words, aim for 25 to 60"),
        _item("Names your goal", 2 if f["summary_has_goal"] else 0, 2),
        _item("One proof point", 2 if f["summary_has_proof"] else 0, 2),
        _item("Cliché deduction", -min(1, f["summary_cliche_count"]), 0, "a cliché in the summary" if f["summary_cliche_count"] else ""),
    ])


def score_contact(f):
    em = {"professional": 3, "casual": 1, None: 0}[f["email_quality"]]
    li = {"custom": 3, "random": 1, None: 0}[f["linkedin_quality"]]
    return _cat("contact", [
        _item("Professional email", em, 3, {"professional": "name-based email", "casual": "email looks casual or has long numbers", None: "no email found"}[f["email_quality"]]),
        _item("Custom LinkedIn link", li, 3, {"custom": "custom link", "random": "link ends in random characters, customise it", None: "no linkedin.com/in/ link found"}[f["linkedin_quality"]]),
        _item("Phone number", 2 if f["phone"] else 0, 2, "found" if f["phone"] else "not found"),
        _item("City", 2 if f["city"] else 0, 2, f["city"] or "not found near the top"),
    ])


def score_language(f):
    cl = min(4, f["cliche_count"])
    ts = 1 if f["tense_switch"] else 0
    items = [_item("Clichés", 4 - cl, 4, ", ".join(f["cliches"]) if f["cliches"] else "none found"),
             _item("Consistent tense", 1 - ts, 1, "tense switches inside one role" if ts else "consistent")]
    return _cat("language", items, fallback_part=3.0, judged_max=5,
                fallback_note="Typos and voice were not checked by the AI, so 3 of 5 is used")


def score_format(f):
    p = f["pages"]
    pp = 4 if 1 <= p <= 2 else 2 if p == 3 else 0
    bs = f["bullet_share"]
    bp = 4 if bs >= .8 else 2 if bs >= .5 else 0
    items = [_item("Page count", pp, 4, f"{p} page(s)" + (" (estimated)" if f["pages_estimated"] else "")),
             _item("Bullets, not paragraphs", bp, 4, f"{round(bs * 100)}% of body lines are bullets")]
    return _cat("format", items, fallback_part=2.0 if f["dates_consistent"] else 0.0, judged_max=2,
                fallback_note="Date style check used. Fonts were not checked" )


def score_fit(f, target):
    kws = TARGET_KEYWORDS.get(target, [])
    low = (f["summary_text"] + "\n" + "\n".join(f["bullets"]) + "\n" + " ".join(f["sections_found"])).lower()
    hits = [k for k in kws if k in low]
    return _cat("fit", [_item("Words your target reader looks for", min(5, len(hits)), 5, f"{len(hits)} found")], hits=hits)


# ---------- fixes, strengths, rewrites, flags ----------
def build_fixes(f, cats, target):
    fx = []
    def add(cat, text, gain):
        if gain > 0.05:
            fx.append({"category": cat, "text": text, "gain": gain})
    n = f["bullet_total"]
    if n == 0:
        add("evidence", "Add bullets under Projects, Experience or Leadership. Each bullet: action verb, what you did, how big, what came of it.", 10)
    else:
        nxt = next((s for s in EVIDENCE_STEPS if s > f["number_share"] + 1e-9), None)
        if nxt:
            need = max(1, math.ceil(nxt * n) - f["bullets_with_number"])
            after = f["bullets_with_number"] + need
            add("evidence", f"Add a number, scale or result to {need} more bullet(s), so {after} of your {n} bullets carry one. "
                f"Use [__] where you do not know the figure yet, and keep only numbers you can defend.",
                evidence_points(min(1, after / n)) - evidence_points(f["number_share"]))
    if n:
        wk = f["weak_phrase_count"]
        add("bullets", f"Rewrite {wk} bullet(s) that use weak phrases ({', '.join(f['weak_phrases'])}). Start with what you did, not what you were responsible for.", min(6, 1.5 * wk))
        add("bullets", f"Start every bullet with an action verb such as Led, Built, Organised. {n - f['strong_start_count']} of {n} do not.", max(0, (0.8 - f["strong_start_share"]) * 8))
        add("bullets", "Show what you did and what came of it in each bullet: action, scale, result.", max(0, (0.8 - f["scope_result_share"]) * 6))
    for it in cats["sections"]["items"]:
        if it["name"] == "Order of sections":
            add("sections", f"Fix the order: {it['note']}.", -it["points"])
        elif it["points"] < it["max"]:
            nm = it["name"]
            if nm.startswith("Experience"):
                add("sections", "Add a Leadership or volunteering section (or Experience) with at least two bullets. Plain headings work best.", it["max"] - it["points"])
            else:
                add("sections", f"Add a section titled \"{nm}\" with real content under it." if it["note"] != "heading found but nothing under it"
                    else f"Add content under your {nm} heading.", it["max"] - it["points"])
    for it in cats["summary"]["items"]:
        if it["points"] < it["max"] and it["max"] > 0:
            tip = {"Summary present": "Add a 2 to 3 line summary at the top: who you are, your goal, one proof point.",
                   "Right length (2 to 3 lines)": "Bring your summary to 2 or 3 lines (25 to 60 words).",
                   "Names your goal": "Say in your summary what you are applying for.",
                   "One proof point": "Add one proof point to your summary: a number, award or result."}[it["name"]]
            add("summary", tip, it["max"] - it["points"])
    tips = {"Professional email": "Use a name-based email like firstname.lastname@gmail.com.",
            "Custom LinkedIn link": "Add your LinkedIn link and customise it to linkedin.com/in/yourname.",
            "Phone number": "Add a phone number in the header.", "City": "Add your city under your name."}
    for it in cats["contact"]["items"]:
        if it["points"] < it["max"]:
            add("contact", tips[it["name"]], it["max"] - it["points"])
    if f["cliche_count"]:
        add("language", f"Replace clichés ({', '.join(f['cliches'])}) with proof: a number, an award or a result.", min(4, f["cliche_count"]))
    if f["tense_switch"]:
        add("language", "Use present tense only for your current role and past tense for earlier ones.", 1)
    if not 1 <= f["pages"] <= 2:
        add("format", f"Bring your CV to 1 or 2 pages (now {f['pages']}).", 4 - cats["format"]["items"][0]["points"])
    if f["bullet_share"] < .8:
        add("format", "Turn long paragraphs into bullets of one or two lines.", 4 - cats["format"]["items"][1]["points"])
    if not f["dates_consistent"]:
        add("format", "Use one date style everywhere (for example Jan 2024 to Mar 2025).", 2)
    if target in TARGET_KEYWORDS and cats["fit"]["points"] < 5:
        missing = [k for k in TARGET_KEYWORDS[target] if k not in cats["fit"]["hits"]][:4]
        add("fit", f"Use words your {target} reader looks for where they are true for you, for example: {', '.join(missing)}.", 5 - cats["fit"]["points"])
    scale = 1.0 if target in TARGET_KEYWORDS else 100 / 95
    for x in fx:
        x["gain"] = round(x["gain"] * scale, 1)
    order = {k: i for i, k in enumerate(MAX_POINTS)}
    fx.sort(key=lambda x: (-x["gain"], order[x["category"]]))
    return fx


def build_strengths(f, cats):
    s = []
    if cats["contact"]["items"][0]["points"] == 3:
        s.append(("Professional email", "Recruiters judge you in the first five seconds, and a name-based email passes that test."))
    if f["bullet_total"] >= 3 and f["number_share"] >= .4:
        s.append(("Numbers in your bullets", f"{round(f['number_share'] * 100)}% of your bullets carry a number, which makes your work easy to picture."))
    if f["bullet_total"] >= 3 and f["strong_start_share"] >= .8:
        s.append(("Strong verbs", "Most bullets start with an action verb, so they read as things you did."))
    if f["bullet_total"] >= 3 and f["weak_phrase_count"] == 0:
        s.append(("No weak phrases", "No \"responsible for\" or \"helped with\", so each bullet shows your own part."))
    if cats["sections"]["points"] >= 12:
        s.append(("Complete sections", "You have the key sections, so the reader finds what they need fast."))
    if cats["contact"]["items"][1]["points"] == 3:
        s.append(("Custom LinkedIn link", "A clean LinkedIn link tells the reader you take your profile seriously."))
    if f["summary_present"] and f["summary_has_goal"] and f["summary_has_proof"] and f["summary_length_ok"]:
        s.append(("Clear opening summary", "Your summary says who you are, what you want and gives one proof point."))
    if 1 <= f["pages"] <= 2 and f["bullet_share"] >= .8:
        s.append(("Easy to scan", "Right length and mostly bullets, so a busy reader can scan it."))
    if f["cliche_count"] == 0:
        s.append(("No clichés", "You avoid empty words like \"passionate\", so your evidence does the talking."))
    return [{"title": t, "reason": r} for t, r in s[:3]]


def _weakness(b):
    low = b.lower()
    return 3 * any(p in low for p in WEAK_PHRASES) + 2 * (not is_strong_start(_first_word(b))) + 2 * (not has_number(b)) + (1 if len(b.split()) < 6 else 0)


def build_rewrites(f):
    out = []
    for b in sorted(f["bullets"], key=_weakness, reverse=True)[:2]:
        if _weakness(b) == 0:
            continue
        rest = b
        for p in WEAK_PHRASES:
            rest = re.sub(r"^\s*" + re.escape(p) + r"\s+", "", rest, flags=re.I)
        rest = rest.rstrip(". ")
        label = ""
        m = re.match(r"^(.{3,60}?)\s+[—–-]\s+(.+)$", rest)          # "Programme name — what you did"
        if m and len(m.group(1).split()) <= 8:
            label, rest = m.group(1) + ": ", m.group(2)
        w0 = rest.split()[0] if rest.split() else ""
        strong = is_strong_start(_first_word(rest))
        if not strong and w0[1:].islower() and w0.lower().endswith(("ing", "ed")):
            rest = rest[:1].lower() + rest[1:]
        tail = []
        if not has_number(b):
            tail.append("[__ how many, how often or how big]")
        if not any(r in b.lower() for r in RESULT_WORDS):
            tail.append("which [__ result you can defend]")
        if strong and not tail and not any(p in b.lower() for p in WEAK_PHRASES):
            continue
        text = label + ("" if strong else "[Strong verb] ") + rest + ((", " + ", ".join(tail)) if tail else "")
        note = "Replace the weak phrase with what you actually did." if any(p in b.lower() for p in WEAK_PHRASES) else ""
        out.append({"original": b, "rewrite": text + ".", "note": note})
    return out


def build_flags(f):
    checks = [
        (r"\b(led|organi[sz]ed|coordinated|chaired)\b", r"\b(attended|participated|member of|joined)\b", "Did you lead this or take part? Say which."),
        (r"\b(prototype|mockup|mock-up|demo)\b", r"\b(deployed|launched|live|rolled out|in use)\b", "Is this a prototype or a live product used by real people? Say which."),
        (r"\b(total|so far|in total|overall)\b(?!.*\b(cumulative|per year|yearly|each year|annual)\b)", r"\d", "Is this number cumulative or per year? Say which."),
        (r"\b(founded|started|created|launched)\b", r"\b(group|club|society|community|initiative|ngo|foundation)\b", "Is the group registered or informal? Say which."),
        (r"\b(team|group)\b", r"\b(built|won|achieved|increased|reduced|raised)\b", "Was this a team result or your own part of it? Say which."),
        (r"\bgraduates?\b", r"\b(trained|taught|mentored|reached)\b", "Were these undergraduates or graduates? Say which."),
    ]
    flags = []
    for b in f["bullets"]:
        low = b.lower()
        for a, c, q in checks:
            if re.search(a, low) and re.search(c, low):
                flags.append({"bullet": b[:140], "question": q})
                break
    return flags[:3]


# ---------- main entry ----------
def score_rules(f, target=None):
    target = target if target in TARGET_KEYWORDS else None
    cats = {"evidence": score_evidence(f), "bullets": score_bullets(f), "sections": score_sections(f), "summary": score_summary(f),
            "contact": score_contact(f), "language": score_language(f), "format": score_format(f), "fit": score_fit(f, target)}
    use = [k for k in MAX_POINTS if k != "fit" or target]
    raw = sum(cats[k]["points"] for k in use)
    total = round(raw * 100 / sum(MAX_POINTS[k] for k in use))
    fixes = build_fixes(f, cats, target)
    top = fixes[0] if fixes else None
    band = band_for(total)
    nxt = ("Go back to Build mode and rebuild your CV from your master CV, then upload it again." if band == "Rebuild"
           else f"Make fix 1 ({top['text'].split('.')[0]}), then upload again to see your new score." if top else "Tailor this CV to each opportunity you apply for.")
    required = ["education", "projects", "skills"]
    missing = [SECTION_NAMES[k] for k in required if k not in f["sections_found"]]
    if not ({"experience", "leadership"} & set(f["sections_found"])):
        missing.append("Leadership or volunteering (or Experience)")
    missing += [SECTION_NAMES[k] for k in ("awards", "memberships", "certifications") if k not in f["sections_found"]]
    return {
        "rubric_version": RUBRIC_VERSION, "mode": "rules_only", "target": target or "none",
        "score": total, "band": band, "approximate": True,
        "categories": {k: cats[k] for k in use},
        "strengths": build_strengths(f, cats), "fixes": fixes[:3], "all_fixes": fixes,
        "missing_sections": missing, "rewrites": build_rewrites(f), "flags": build_flags(f),
        "next_step": nxt,
        "defend_line": "Keep only numbers you can defend in an interview.",
        "less_certain": [],
        "notices": ["Checked by rules only. The AI check was not used for this result."]
                   + ([f"Your CV still has {len(f['placeholders'])} unfilled placeholder(s) in square brackets, for example {f['placeholders'][0][:40]}. "
                       "Fill each one with a real detail or delete it before you send the CV."] if f["placeholders"] else []),
        "short_cv_note": "Few bullets found. Add more under Projects or Volunteering." if 0 < f["bullet_total"] < 6 else "",
    }
