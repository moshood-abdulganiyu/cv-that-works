"""Show what the engine saw in chosen generated test CVs (made-up CVs only).
Run from the project root, for example:  python -m tests.diagnose 104 64 74
Use it to tell an ENGINE problem (bullets or sections not found) from a PLAN problem (the CV really is that weak)."""
import re
import sys
from pathlib import Path

from core.engine import score_file

G = Path(__file__).parent / "samples" / "generated"


def main(ids):
    for i in ids:
        path = next((p for p in G.glob("*.txt") if re.match(r"^(?:cv|csv)_0*%d\.txt$" % int(i), p.name, re.I)), None)
        if not path:
            print(f"cv {i}: file not found")
            continue
        r = score_file(path.name, path.read_bytes(), None, allow_txt=True)
        f = r["facts"]
        txt = path.read_text(encoding="utf-8", errors="ignore")
        raw_lines = txt.count("\n- ") + txt.count("\n\u2022")
        print(f"\n=== {path.name}  score {r['score']} ({r['band']}, scored with no target)")
        print(f"bullet lines in the file: about {raw_lines} | bullets the engine counted: {f['bullet_total']} ({f['bullet_source']})")
        print(f"bullets with a number: {round(f['number_share'] * 100)}% | start with an action verb: {f['strong_start_count']} | weak phrases: {f['weak_phrase_count']}")
        print(f"sections found: {', '.join(f['sections_found'])}")
        print(f"summary found: {f['summary_present']} (headed: {f['summary_headed']}, {f['summary_words']} words) | email: {f['email_quality']} | linkedin: {f['linkedin_quality']} | phone: {bool(f['phone'])} | city: {f['city']}")
        for c in r["categories"].values():
            print(f"  {c['label']:<32}{c['points']:>5} / {c['max']}")
    print("\nCompare 'bullet lines in the file' with 'bullets the engine counted'. If the file has many more, the engine missed them (report it).")


if __name__ == "__main__":
    main(sys.argv[1:] or ["104"])
