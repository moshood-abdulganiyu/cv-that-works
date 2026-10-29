"""Run the rules engine on the generated test CVs and compare each score with its planned zone.
TEST USE ONLY. These CVs are made up and never go into training.
Run from the project root:  python -m tests.run_generated
Reads:  tests/samples/generated/*.txt  and  tests/samples/generated/manifest.csv (optional)
Writes: tests/samples/generated/results.csv
Rules only: no AI call is made, so it costs nothing and gives the same answer every time."""
import csv
import re
import statistics
from collections import Counter
from pathlib import Path

from core.checker import BULLET_RE, heading_key
from core.engine import score_file
from core.reader import CVReadError

G = Path(__file__).parent / "samples" / "generated"
ID_CELL = re.compile(r"^(?:cv|csv)?_?\d+(?:\.txt)?$", re.I)
NO_VARIANT = {"", "no", "none", "-", "false", "n", "0"}


def num_key(s):
    m = re.search(r"\d+", s or "")
    return int(m.group(0)) if m else None


def load_manifest():
    """Merge the plan and every batch CSV block. Repeated header lines, code fences and tracker lines are skipped."""
    rows, header = {}, None
    path = G / "manifest.csv"
    if not path.exists():
        return rows
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.reader(fh):
            cells = [c.strip() for c in r]
            if not any(cells):
                continue
            if cells[0].lower() == "id":
                header = [c.lower() for c in cells]
                continue
            if header is None or not ID_CELL.match(cells[0]):
                continue
            rows.setdefault(num_key(cells[0]), {}).update(dict(zip(header, cells)))
    return rows


def parse_zone(z):
    m = re.match(r"\s*(\d+)\s*[-\u2013]\s*(\d+)", z or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def heading_candidates(text):
    """Short title-like lines that follow a blank line but are not recognised as a section heading."""
    lines = text.replace("\r", "").split("\n")
    out = []
    for i, l in enumerate(lines):
        s = l.strip()
        if i == 0 or not s or lines[i - 1].strip() or i + 1 >= len(lines) or not lines[i + 1].strip():
            continue
        if (len(s.split()) <= 5 and s[:1].isupper() and not re.search(r"\d|\||@", s) and not s.endswith((".", ";", ","))
                and not BULLET_RE.match(s) and heading_key(s)[0] is None):
            out.append(s)
    return out


def main():
    files = sorted(p for p in G.glob("*.txt") if re.match(r"^(?:cv|csv)_\d+\.txt$", p.name, re.I))
    if not files:
        print(f"No .txt files found in {G}. Put the generated CVs there first.")
        return
    manifest = load_manifest()
    rows, cand, seen = [], Counter(), set()
    for f in files:
        k = num_key(f.stem)
        m = manifest.get(k, {})
        seen.add(k)
        target = (m.get("target") or "").strip().lower()
        target = None if target in ("", "none", "not sure") else target
        text = f.read_text(encoding="utf-8", errors="ignore")
        try:
            r = score_file(f.name, f.read_bytes(), target, allow_txt=True)
        except CVReadError as e:
            print(f"{f.name}: cannot read ({e.message})")
            continue
        for h in set(heading_candidates(text)):
            cand[h] += 1
        zone = parse_zone(m.get("zone"))
        score = r["score"]
        status, gap = "no plan", ""
        if zone:
            lo, hi = zone
            status, gap = ("OK", 0) if lo <= score <= hi else (("LOW", score - lo) if score < lo else ("HIGH", score - hi))
        cats = r["categories"]
        short = sorted(((c["max"] - c["points"], c["label"]) for c in cats.values()), reverse=True)[:3]
        facts = r["facts"]
        rows.append({
            "id": f.stem, "course": m.get("course", ""), "group": m.get("group", ""), "target": target or "none",
            "heading_variant": m.get("heading_variant", ""), "planned_flaws": m.get("planned_flaws", ""), "planned_zone": m.get("zone", ""), "score": score, "band": r["band"],
            "status": status, "gap": gap, "words": facts["word_count"], "bullets": facts["bullet_total"],
            "number_pct": round(facts["number_share"] * 100), "sections_found": " ".join(facts["sections_found"]),
            **{f"pts_{k}": c["points"] for k, c in cats.items()},
            "biggest_losses": "; ".join(f"{lab} -{round(d, 1)}" for d, lab in short if d > 0.05),
        })

    out = G / "results.csv"
    cols = list(rows[0].keys())
    for r in rows:
        for c in r:
            if c not in cols:
                cols.append(c)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, restval="")
        w.writeheader()
        w.writerows(rows)

    # ---------- summary ----------
    print(f"\nScored {len(rows)} CVs (rules only). Full table saved to {out}")
    no_plan = [r["id"] for r in rows if r["status"] == "no plan"]
    missing_files = sorted(set(manifest) - seen)
    if no_plan:
        print(f"Files with no plan row (zone not checked): {len(no_plan)}  e.g. {', '.join(no_plan[:5])}")
    if missing_files:
        print(f"Plan rows with no file yet: {len(missing_files)}")

    print("\nZONE CHECK")
    print(f"{'planned zone':<14}{'CVs':>5}{'in zone':>9}{'too low':>9}{'too high':>10}{'mean':>7}{'min':>5}{'max':>5}")
    zones = sorted({r["planned_zone"] for r in rows if r["status"] != "no plan"}, key=lambda z: parse_zone(z) or (0, 0))
    means = []
    for z in zones:
        zr = [r for r in rows if r["planned_zone"] == z]
        sc = [r["score"] for r in zr]
        means.append(statistics.mean(sc))
        print(f"{z:<14}{len(zr):>5}{sum(r['status'] == 'OK' for r in zr):>9}{sum(r['status'] == 'LOW' for r in zr):>9}"
              f"{sum(r['status'] == 'HIGH' for r in zr):>10}{statistics.mean(sc):>7.1f}{min(sc):>5}{max(sc):>5}")
    if means:
        print("Zone averages rise in the right order:", "yes" if all(a < b for a, b in zip(means, means[1:])) else "NO, check the zones above")
    planned = [r for r in rows if r["status"] != "no plan"]
    if planned:
        print(f"In zone overall: {sum(r['status'] == 'OK' for r in planned)} of {len(planned)}")

    off = sorted((r for r in planned if r["status"] != "OK"), key=lambda r: -abs(r["gap"]))
    if off:
        print("\nOUT OF ZONE (largest gap first, top 25)")
        for r in off[:25]:
            print(f"  {r['id']:<8}{r['course'][:26]:<27}plan {r['planned_zone']:<8}got {r['score']:<4}({r['status']} by {abs(r['gap'])})  {r['biggest_losses']}")

    var = [r for r in rows if str(r["heading_variant"]).strip().lower() not in NO_VARIANT]
    if var:
        print("\nHEADING VARIANT CVs. (planned) = the plan removed it on purpose. ENGINE MISS? = the CV probably has it and the engine did not")
        for r in var:
            have = set(r["sections_found"].split())
            planned = set(re.findall(r"X\d", str(r["planned_flaws"]).upper()))
            checks = (("Education", "education" in have, "X2"), ("Projects", "projects" in have, "X1"), ("Skills", "skills" in have, "X3"),
                      ("Experience or Leadership", bool({"experience", "leadership"} & have), "X4"))
            miss = [n + (" (planned)" if code in planned else " (ENGINE MISS?)") for n, ok, code in checks if not ok]
            print(f"  {r['id']:<8}{r['course'][:24]:<25}variant: {str(r['heading_variant'])[:30]:<31}{'; '.join(miss) if miss else 'all found'}")

    if cand:
        print("\nHEADINGS THE ENGINE DID NOT RECOGNISE (count of CVs), add real ones to rubric.py")
        for h, n in cand.most_common(25):
            print(f"  {n:>3}  {h}")
    print("\nDone. Paste this summary into the chat. Do not paste the CV text.")


if __name__ == "__main__":
    main()
