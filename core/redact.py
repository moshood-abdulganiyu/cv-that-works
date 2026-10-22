"""Remove personal details from CV text before anything goes to the outside AI.
Removes: name, email addresses, phone numbers, links and social handles, and home address lines.
It does NOT make a CV anonymous: school, club, employer and town names stay. The consent line says so."""
import re

EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")
URL_RE = re.compile(r"(?:https?://|www\.)\S+|(?:linkedin|github|twitter|instagram|facebook|behance)\.com/\S*", re.I)
HANDLE_RE = re.compile(r"(?<![\w.])@[A-Za-z0-9_.]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{8,}\d")
YEAR_RANGE_RE = re.compile(r"^\s*(?:19|20)\d{2}\D{1,4}(?:19|20)\d{2}\s*$")
ADDRESS_WORD_RE = re.compile(r"\b(street|st\.|road|rd\.|avenue|ave\.|close|crescent|estate|layout|junction|opposite|opp\.|p\.?\s?m\.?\s?b\.?)\b", re.I)


def _phone_sub(m):
    digits = re.sub(r"\D", "", m.group(0))
    if 10 <= len(digits) <= 15 and not YEAR_RANGE_RE.match(m.group(0)):
        return "[phone]"
    return m.group(0)


def name_words(name_line):
    """Words from the top line of the CV, if it looks like a name (short, no email or digits)."""
    s = (name_line or "").strip()
    if not s or "@" in s or re.search(r"\d", s) or len(s.split()) > 6:
        return []
    return sorted(set(re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", s)), key=len, reverse=True)


def _is_address_line(line):
    words = line.split()
    return len(words) <= 10 and bool(re.search(r"\d", line)) and bool(ADDRESS_WORD_RE.search(line))


def redact_text(text, name_line=""):
    if not text:
        return ""
    out = []
    for line in str(text).split("\n"):
        if _is_address_line(line):
            continue
        out.append(line)
    t = "\n".join(out)
    t = EMAIL_RE.sub("[email]", t)
    t = URL_RE.sub("[link]", t)
    t = HANDLE_RE.sub("[handle]", t)
    t = PHONE_RE.sub(_phone_sub, t)
    for w in name_words(name_line):
        t = re.sub(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", "[name]", t, flags=re.I)
    return t
