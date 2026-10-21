"""Single entry point: file in, explainable report out. The API (step 4) will call score_file."""
import sys
import time
from pathlib import Path

from .checker import check_cv
from .reader import CVReadError, read_document
from .rules import score_rules


def score_text(text, pages=1, target=None, pages_estimated=False, links=None):
    t0 = time.perf_counter()
    facts = check_cv(text, pages, pages_estimated, links)
    report = score_rules(facts, target)
    report["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    report["facts"] = {k: v for k, v in facts.items() if k not in ("bullets", "summary_text")}
    return report


def score_file(name, data, target=None, allow_txt=False):
    doc = read_document(name, data, allow_txt=allow_txt)
    return score_text(doc["text"], doc["pages"], target, doc["pages_estimated"], doc.get("links"))


def print_report(r):
    print(f"\n{r['band'].upper()}   {r['score']}/100 (approximate)   target: {r['target']}   [{r['rubric_version']}, {r['mode']}]")
    for c in r["categories"].values():
        print(f"  {c['label']:<32}{c['points']:>5} / {c['max']}")
    print("\nWorking:"); [print(f"  + {s['title']}: {s['reason']}") for s in r["strengths"]]
    print("Top fixes:"); [print(f"  {i}. (+{x['gain']}) {x['text']}") for i, x in enumerate(r["fixes"], 1)]
    print("Missing:", ", ".join(r["missing_sections"]) or "none")
    for w in r["rewrites"]:
        print("Rewrite:", w["original"][:80], "\n      ->", w["rewrite"])
    for fl in r["flags"]:
        print("Check:", fl["question"], "|", fl["bullet"][:70])
    print("Next:", r["next_step"], "\n", r["defend_line"])


if __name__ == "__main__":
    # usage: python -m core.engine path/to/cv.pdf [target]
    path = Path(sys.argv[1])
    try:
        print_report(score_file(path.name, path.read_bytes(), sys.argv[2] if len(sys.argv) > 2 else None, allow_txt=True))
    except CVReadError as e:
        print("Cannot read file:", e.message)
