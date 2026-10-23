"""Step 8: run the calibration ladder with the AI judge on, several times each.
Checks three things: the order of the rungs is kept, weak lands near 40 and strong near 90, and repeat runs stay in one band.
Needs a real Gemini key in this PowerShell window (see the message printed if it is missing). Nothing is stored or printed from the CVs.
Run: python -m tests.repeat_run [runs per CV, default 3] [target, default internship]"""
import os
import sys
import time

from core.engine import score_text
from core.rubric import BANDS
from tests import ladder

PAUSE = 7        # seconds between AI calls, keeps us under about 10 requests a minute


def band_index(score):
    names = [n for _, n in BANDS]            # best band first
    return names.index(next(n for floor, n in BANDS if score >= floor))


def items():
    raw = ladder.rungs()
    if isinstance(raw, dict):
        raw = list(raw.items())
    out = []
    for i, x in enumerate(raw, 1):
        if isinstance(x, str):
            out.append((f"rung {i}", x)); continue
        if isinstance(x, dict):
            x = list(x.values())
        text = next((v for v in x if isinstance(v, str) and len(v) > 200), None)
        name = next((v for v in x if isinstance(v, str) and len(v) <= 200), f"rung {i}")
        if text is None:
            raise SystemExit(f"Could not read rung {i} from tests/ladder.py (got {type(x).__name__}). Paste me the rungs() function.")
        out.append((name, text))
    return out


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    target = sys.argv[2] if len(sys.argv) > 2 else "internship"
    if not os.environ.get("GEMINI_API_KEY"):
        print('No GEMINI_API_KEY in this window. Set it for this window only (never save it in a file), then run again:\n'
              '  $env:GEMINI_API_KEY = "paste-your-key"\n'
              '  $env:GEMINI_MODEL = "gemini-3.5-flash-lite"\n'
              '  $env:GEMINI_MODEL_BACKUP = "gemini-3.1-flash-lite"')
        return 1
    rows = items()
    print(f"{len(rows)} CVs x {runs} runs, target {target}. About {round(len(rows) * runs * (PAUSE + 5) / 60)} minutes. Please wait.\n")
    results, ai_failed = [], 0
    for name, text in rows:
        rules = score_text(text, 1, target, judge=False)["score"]
        scores, bands, notes = [], [], []
        for _ in range(runs):
            time.sleep(PAUSE)
            r = score_text(text, 1, target, judge=True)
            if r["judge"].get("ok") and r["mode"] == "blended":
                scores.append(r["score"]); bands.append(r["band"])
                if r.get("less_certain"):
                    notes.append(",".join(r["less_certain"]))
            else:
                ai_failed += 1; notes.append("AI " + str(r["judge"].get("reason")))
        results.append({"name": name, "rules": rules, "scores": scores, "bands": bands, "notes": notes})
        print(f"{name[:34]:<34} rules {rules:>3}   blended {scores}   {sorted(set(bands))}   {'; '.join(sorted(set(notes)))}")
    print()
    good = [r for r in results if r["scores"]]
    wobble = 0
    for r in good:
        spread = max(r["scores"]) - min(r["scores"])
        steps = max(band_index(s) for s in r["scores"]) - min(band_index(s) for s in r["scores"])
        verdict = "same band" if steps == 0 else "next band over" if steps == 1 else "TOO WIDE"
        wobble += steps > 0
        print(f"  {r['name'][:34]:<34} spread {spread:>2} points, {verdict}")
    if len(good) < 2:
        print("\nToo few AI results to judge. Check the AI notes above and try again in a few minutes.")
        return 1
    mean = lambda r: sum(r["scores"]) / len(r["scores"])
    by_rules = [r["name"] for r in sorted(good, key=lambda r: -r["rules"])]
    by_blend = [r["name"] for r in sorted(good, key=lambda r: -mean(r))]
    print(f"\nOrder kept after blending: {'YES' if by_rules == by_blend else 'NO'}")
    if by_rules != by_blend:
        print("  rules order :", by_rules, "\n  blended order:", by_blend)
    print(f"Strongest CV blended mean: {max(map(mean, good)):.0f} (aim near 90).  Weakest: {min(map(mean, good)):.0f} (aim near 40).")
    print(f"Runs where the AI was not used: {ai_failed}.  CVs that moved a band between runs: {wobble} of {len(good)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
