"""The one shared checker. Turns CV text into a dictionary of facts.
Scoring (rules.py) and later the AI judge and trained model all read these same facts."""
import re

from .rubric import (ALIAS_TO_SECTION, BODY_SECTIONS, CASUAL_EMAIL_WORDS, CITIES, CLICHES, ACTION_VERBS,
                     IRREGULAR_PAST, PLACES, RESULT_WORDS, WEAK_PHRASES, WEAK_STARTS)

BULLET_RE = re.compile(r"^\s*(?:[•●▪◦○·‣⁃►➤]\s*|[-–*]\s*)")
ENTRY_END_RE = re.compile(r"[-–—]+\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+)?(?:(?:19|20)\d{2}|present|current)\s*$", re.I)
MARKER_ONLY_RE = re.compile(r"^[•●▪◦○·‣⁃►➤\-–—*]+$")
FUZZY_HEADINGS = [("leadership", ["leadership", "volunteering", "community service", "extracurricular"]), ("projects", ["projects"]),
                  ("awards", ["awards", "honours", "honors", "scholarships", "achievements"]), ("memberships", ["memberships", "affiliations", "associations"]),
                  ("certifications", ["certifications", "certificates", "training"]), ("experience", ["experience", "internship", "internships", "employment"]),
                  ("skills", ["skills"]), ("education", ["education"]), ("summary", ["summary", "profile", "objective"]), ("languages", ["languages"])]
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL_RE = re.compile(r"(?:https?://|www\.)\S+|linkedin\.com/\S+", re.I)
LINKEDIN_RE = re.compile(r"linkedin\.com/in/([A-Za-z0-9\-_%]+)", re.I)
PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{8,}\d")
CURRENT_RE = re.compile(r"\b(present|current|ongoing|till date|to date|now)\b", re.I)
ABBR_MONTH = re.compile(r"\b(?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(?:19|20)\d{2}\b")
FULL_MONTH = re.compile(r"\b(?:January|February|March|April|June|July|August|September|October|November|December)\s+(?:19|20)\d{2}\b")
NUM_DATE = re.compile(r"\b\d{1,2}/(?:\d{2}|\d{4})\b")

BASE_FORMS = set()
for _w in ACTION_VERBS:
    if _w in IRREGULAR_PAST:
        BASE_FORMS.add(IRREGULAR_PAST[_w])
    elif _w.endswith("ed"):
        BASE_FORMS.update({_w[:-1], _w[:-2]})


def _first_word(s):
    m = re.match(r"[A-Za-z'\-]+", s.strip())
    return m.group(0).lower().replace("'", "").strip("-") if m else ""


def _core(w):
    return w.split("-")[-1] if w else w


def is_past(w):
    w = _core(w)
    return w in IRREGULAR_PAST or (w.endswith("ed") and len(w) > 3)


def is_present(w):
    w = _core(w)
    return w in BASE_FORMS or (w.endswith("s") and (w[:-1] in BASE_FORMS or w[:-2] in BASE_FORMS))


def is_strong_start(w):
    w = _core(w)
    if not w or w in WEAK_STARTS:
        return False
    return w in ACTION_VERBS or w in BASE_FORMS or is_past(w)


def has_number(s):
    return bool(re.search(r"\d", YEAR_RE.sub(" ", s)))


def heading_key(line):
    """Return the section key if this line is a heading, plus any text on the same line ("Skills: Excel, Python")."""
    if BULLET_RE.match(line):
        return None, None
    s = re.sub(r"\s+", " ", line.strip().strip(":").strip().lower().replace("&", "and"))
    if len(s.split()) <= 6 and s in ALIAS_TO_SECTION:
        return ALIAS_TO_SECTION[s], None
    m = re.match(r"^([A-Za-z &/]{3,40}):\s*(.+)$", line.strip())
    if m:
        k = re.sub(r"\s+", " ", m.group(1).strip().lower().replace("&", "and"))
        if k in ALIAS_TO_SECTION:
            return ALIAS_TO_SECTION[k], m.group(2)
    # titles like "AI Community & Leadership Experience": short, capitalised, no date, keyword at the end or joined by &/and/comma
    raw = line.strip().rstrip(":")
    if (len(raw.split()) <= 8 and raw[:1].isupper() and not raw.endswith((".", ";", ",")) and "|" not in raw
            and not YEAR_RE.search(raw) and not re.search(r"\d", raw)):
        words = re.findall(r"[a-z]+", raw.lower())
        joined = bool(re.search(r"&|,|\band\b", raw))
        for key, kws in FUZZY_HEADINGS:
            if any(k in words and (joined or k in words[-2:]) for k in kws):
                return key, None
    return None, None


def _header_like(line):
    s = line.strip()
    return "|" in s or bool(ENTRY_END_RE.search(s)) or (len(s.split()) <= 4 and not s.endswith((".", ";", ",")))


DATE_RANGE_RE = re.compile(r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*)?(?:19|20)\d{2}\s*[-\u2013\u2014]+\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*)?(?:(?:19|20)\d{2}|present|current)|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*[-\u2013\u2014]+\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*(?:19|20)\d{2}", re.I)


def _is_header_line(s):
    return "|" in s or bool(DATE_RANGE_RE.search(s)) or bool(ENTRY_END_RE.search(s))


def _line_bullets(body_lines):
    """Fallback when the PDF lost its bullet marks: skip role/date lines, and join wrapped lines (a line that starts in lower case)."""
    out = []
    for i, l in enumerate(body_lines):
        nxt = body_lines[i + 1] if i + 1 < len(body_lines) else ""
        if _is_header_line(l) or (len(nxt.split()) <= 6 and DATE_RANGE_RE.search(nxt)):   # a title sitting right above its dates
            continue
        if out and l[:1].islower():
            out[-1] += " " + l
        elif len(l.split()) >= 6:
            out.append(l)
    return out


def _email_quality(email):
    local = email.split("@")[0].lower()
    if re.search(r"\d{4,}", local) or any(w in local for w in CASUAL_EMAIL_WORDS):
        return "casual"
    letters = re.sub(r"[^a-z]", "", local)
    return "professional" if len(letters) >= 4 else "casual"


def _linkedin_quality(slug):
    s = slug.lower()
    if re.search(r"\d{5,}$", s) or re.search(r"-[0-9a-f]{8,}$", s) and re.search(r"\d", s.split("-")[-1]):
        return "random"
    return "custom" if re.search(r"[a-z]{3,}", s) else "random"


def check_cv(text, pages=1, pages_estimated=False, links=None):
    links = links or []
    text = re.sub(r"(?<=\S)([–•])(?=[A-Z][a-z])", r"\n\1", text)   # PDF tools sometimes glue the next bullet onto the line before
    lines = [l.strip() for l in text.split("\n") if l.strip() and not MARKER_ONLY_RE.match(l.strip())]
    f = {"pages": pages, "pages_estimated": pages_estimated, "word_count": len(text.split()), "line_count": len(lines)}

    # sections
    sections, order, top, cur = {}, [], [], None
    for i, line in enumerate(lines):
        key, inline = heading_key(line)
        if key:
            cur = key
            order.append((key, i))
            sections.setdefault(key, [])
            if inline:
                sections[key].append(inline)
        elif cur is None:
            top.append(line)
        else:
            sections[cur].append(line)
    f["sections_found"] = sorted(sections)
    f["section_content_lines"] = {k: len([l for l in v if len(l.split()) >= 2]) for k, v in sections.items()}
    f["section_order"] = [k for k, _ in order]
    f["skills_text"] = " | ".join(sections.get("skills", []))[:600]
    f["name_line"] = (top[0] if top else (lines[0] if lines else ""))[:80]
    f["section_line_index"] = {}
    for k, i in order:
        f["section_line_index"].setdefault(k, i)

    # bullets: join wrapped lines, and treat "• Role ... 2024 - Present" lines as entry headers, not bullets
    body_lines = [l for k in BODY_SECTIONS for l in sections.get(k, [])]
    if not body_lines:
        body_lines = [l for l in lines[len(top):] if heading_key(l)[0] is None]
    items = []   # [kind, text] with kind in header / bullet / text
    for l in body_lines:
        if BULLET_RE.match(l):
            t = BULLET_RE.sub("", l).strip()
            if t:
                items.append(["header" if (len(t.split()) <= 16 and ENTRY_END_RE.search(t)) else "bullet", t])
        elif items and items[-1][0] == "bullet" and not _header_like(l):
            items[-1][1] += " " + l
        else:
            items.append(["text", l])
    markers = [t for k, t in items if k == "bullet"]
    if len(markers) >= 3:
        bullets, source = markers, "markers"
    else:
        bullets, source = _line_bullets(body_lines), "lines"
    paragraphs = [t for k, t in items if k == "text" and len(t.split()) > 35]
    f["bullets"] = bullets
    f["bullet_total"] = len(bullets)
    f["bullet_source"] = source
    f["paragraph_lines"] = len(paragraphs)
    f["bullet_share"] = len(bullets) / (len(bullets) + len(paragraphs)) if (bullets or paragraphs) else 0.0

    firsts = [_first_word(b) for b in bullets]
    f["bullets_with_number"] = sum(has_number(b) for b in bullets)
    f["number_share"] = f["bullets_with_number"] / len(bullets) if bullets else 0.0
    f["strong_start_count"] = sum(is_strong_start(w) for w in firsts)
    f["strong_start_share"] = f["strong_start_count"] / len(bullets) if bullets else 0.0
    f["scope_result_count"] = sum(1 for b, w in zip(bullets, firsts)
                                  if is_strong_start(w) and (has_number(b) or any(r in b.lower() for r in RESULT_WORDS)))
    f["scope_result_share"] = f["scope_result_count"] / len(bullets) if bullets else 0.0
    weak = {}
    for b in bullets:
        for p in WEAK_PHRASES:
            n = len(re.findall(r"\b" + re.escape(p) + r"\b", b.lower()))
            if n:
                weak[p] = weak.get(p, 0) + n
    f["weak_phrases"] = weak
    f["weak_phrase_count"] = sum(weak.values())

    # tense: present-tense bullet starts inside a finished role (a role header without "Present" or "Current")
    switch = False
    if source == "markers":
        header, block = "", []
        for kind, t in items + [["end", ""]]:
            if kind == "bullet":
                block.append(_first_word(t))
                continue
            if block:                                   # a role just ended: check its bullets, then start a new header
                pres = sum(is_present(w) and not is_past(w) for w in block)
                if pres >= 1 and not CURRENT_RE.search(header):
                    switch = True       # present tense in a finished role
                header = t
            else:
                header = (header + " " + t).strip()     # sub-header line under the same role
            block = []
    f["tense_switch"] = switch

    f["placeholders"] = re.findall(r"\[[^\]\n]{0,60}\]", text)

    # clichés
    low = text.lower()
    cl = {}
    for c in CLICHES:
        n = len(re.findall(r"\b" + re.escape(c) + r"\b", low))
        if n:
            cl[c] = n
    f["cliches"] = cl
    f["cliche_count"] = sum(cl.values())

    # summary
    summary_lines = sections.get("summary", [])
    headed = bool(summary_lines)
    if not summary_lines:
        summary_lines = [l for l in top if len(l.split()) >= 15]
    stext = " ".join(summary_lines)
    slow = stext.lower()
    f["summary_present"] = bool(stext)
    f["summary_headed"] = headed
    f["summary_words"] = len(stext.split())
    f["summary_length_ok"] = 25 <= f["summary_words"] <= 60
    f["summary_has_goal"] = bool(re.search(r"seek|aspir|looking|aim|goal|intern|scholarship|master|postgraduate|apply|pursu|want to", slow))
    f["summary_has_proof"] = has_number(stext) or bool(re.search(r"award|won|winner|scholar|first class|distinction|cgpa|gpa|led|founded|published", slow))
    f["summary_cliche_count"] = sum(len(re.findall(r"\b" + re.escape(c) + r"\b", slow)) for c in CLICHES)
    f["summary_text"] = stext

    # contact
    no_email = EMAIL_RE.sub(" ", text)
    emails = EMAIL_RE.findall(text) or [l[7:] for l in links if l.lower().startswith("mailto:")]
    f["email"] = emails[0] if emails else None
    f["email_quality"] = _email_quality(emails[0]) if emails else None
    li = LINKEDIN_RE.search(text) or next((m for m in (LINKEDIN_RE.search(l) for l in links) if m), None)
    f["linkedin"] = bool(li)
    f["linkedin_quality"] = _linkedin_quality(li.group(1)) if li else None
    f["linkedin_mentioned_without_link"] = (not li) and ("linkedin" in low)
    scan = URL_RE.sub(" ", no_email)
    first_block = "\n".join(lines[:12])
    phone = None
    for chunk in (URL_RE.sub(" ", EMAIL_RE.sub(" ", first_block)), scan):
        for m in PHONE_RE.finditer(chunk):
            digits = re.sub(r"\D", "", m.group(0))
            if 10 <= len(digits) <= 15 and not re.fullmatch(r"(?:19|20)\d{2}\D*(?:19|20)\d{2}", m.group(0).strip()):
                phone = m.group(0).strip()
                break
        if phone:
            break
    f["phone"] = phone
    head = "\n".join(top[:6]).lower()
    f["city"] = next((c for c in CITIES if re.search(r"\b" + re.escape(c) + r"\b", head)), None)
    if not f["city"]:
        m = re.search(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?),\s*(" + "|".join(PLACES) + r")\b", "\n".join(top[:6]))
        f["city"] = m.group(1) if m else None
    f["contact_in_top"] = any(EMAIL_RE.search(l) or PHONE_RE.search(l) for l in lines[:8])

    # dates
    styles = set()
    if ABBR_MONTH.search(text):
        styles.add("abbr")
    if FULL_MONTH.search(text):
        styles.add("full")
    if NUM_DATE.search(text):
        styles.add("numeric")
    f["date_styles"] = sorted(styles)
    f["dates_consistent"] = len(styles) <= 1
    return f
