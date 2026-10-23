"""Single entry point: file in, explainable report out. The API (step 4) will call score_file."""
import sys
import time
from pathlib import Path

from .checker import check_cv
from .reader import CVReadError, read_document
from .rules import score_rules


def score_text(text, pages=1, target=None, pages_estimated=False, links=None, judge=False, keep_text=False):
    t0 = time.perf_counter()
    facts = check_cv(text, pages, pages_estimated, links)
    report = score_rules(facts, target)
    if judge:                                   # step 7: AI second opinion. Any failure leaves the rules-only result as it is
        try:
            from .judge import attach_judge, judge_cv
            attach_judge(report, judge_cv(facts, None if report["target"] == "none" else report["target"]))
            from .blend import blend_report          # step 8: blend the two readers into one score
            if report.get("judge", {}).get("ok"):
                report.update(blend_report(report))
        except Exception:
            report["judge"] = {"ok": False, "reason": "error"}
    if keep_text:                               # step 8: only when the student ticked the save box. Redacted text, removed again by service.py
        try:
            from .redact import redact_text
            report["_saved_text"] = redact_text(text, facts.get("name_line"))
        except Exception:
            pass
    report["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    report["facts"] = {k: v for k, v in facts.items() if k not in ("bullets", "summary_text", "name_line", "skills_text")}
    return report


def score_file(name, data, target=None, allow_txt=False, judge=False, keep_text=False):
    doc = read_document(name, data, allow_txt=allow_txt)
    return score_text(doc["text"], doc["pages"], target, doc["pages_estimated"], doc.get("links"), judge=judge, keep_text=keep_text)


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
