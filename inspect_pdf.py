"""Run on your own computer. Prints how the checker sees a CV PDF. Nothing is uploaded anywhere.
Usage (from C:\\Code\\cv-that-works):  python inspect_pdf.py "C:\\path\\to\\cv.pdf"
Delete your name, email and phone from the printed text before pasting it into the chat."""
import sys
from pypdf import PdfReader
from core.reader import _tidy
from core.checker import check_cv
r = PdfReader(sys.argv[1])
raw = "\n".join((p.extract_text() or "") for p in r.pages)
text = _tidy(raw)
f = check_cv(text, len(r.pages))
print("bullet source:", f["bullet_source"], "| bullets found:", f["bullet_total"])
print("\n--- first 45 lines as the checker sees them (repr shows hidden characters) ---")
for line in text.split("\n")[:45]:
    print(repr(line[:110]))
print("\n--- bullets the tool would score ---")
for b in f["bullets"][:12]:
    print("*", b[:110])
