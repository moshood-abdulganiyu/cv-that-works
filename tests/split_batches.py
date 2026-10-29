"""Split the other AI's pasted output into one .txt file per CV, plus manifest.csv.
TEST USE ONLY. The CVs are made up and never go into training.
Put everything the AI sent (the plan and every batch) into tests/samples/generated/raw_batches.txt, then run:
    python -m tests.split_batches
Safe to re-run: it rewrites the same files. Add new batches to the end of raw_batches.txt and run it again."""
import re
from pathlib import Path

G = Path(__file__).parent / "samples" / "generated"
START = re.compile(r"^[#*\s]*FILE:\s*([\w.\-]+)", re.I)
END = re.compile(r"^[#*\s]*END FILE", re.I)
ROW = re.compile(r"^\s*(?:id,|(?:cv|csv)_\d+,)", re.I)


def main():
    raw_path = G / "raw_batches.txt"
    if not raw_path.exists():
        print(f"Cannot find {raw_path}. Save everything the AI sent into that file first.")
        return
    lines = raw_path.read_text(encoding="utf-8", errors="ignore").replace("\r", "").split("\n")
    files, rows, cur, name = {}, [], None, None
    for line in lines:
        if cur is None:
            m = START.match(line)
            if m:
                name, cur = m.group(1), []
            elif ROW.match(line):
                rows.append(line.strip())
        elif END.match(line):
            body = [l for l in cur if not l.strip().startswith("```")]
            while body and not body[0].strip():
                body.pop(0)
            while body and not body[-1].strip():
                body.pop()
            files[name if name.lower().endswith(".txt") else name + ".txt"] = "\n".join(body) + "\n"
            cur = None
        else:
            cur.append(line)
    if cur is not None:
        print(f"Warning: {name} has no END FILE line, so it was skipped. Check the end of your raw file.")
    G.mkdir(parents=True, exist_ok=True)
    for n, body in files.items():
        (G / n).write_text(body, encoding="utf-8")
    (G / "manifest.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    nums = sorted(int(re.search(r"\d+", n).group(0)) for n in files)
    print(f"Wrote {len(files)} CV files and {len(rows)} manifest lines to {G}")
    if nums:
        gaps = sorted(set(range(nums[0], nums[-1] + 1)) - set(nums))
        print(f"Numbers {nums[0]} to {nums[-1]}." + (f" Missing: {gaps}" if gaps else " No gaps."))
    bad = [n for n, b in files.items() if re.search(r"(?i)zone|planned_flaws|#### ", b) or len(b.split()) < 150]
    if bad:
        print("Check these files by eye (very short, or contain plan notes):", ", ".join(sorted(bad)[:15]))


if __name__ == "__main__":
    main()
