# CV That Works

Free CV scoring tool for first-time CVs (BSG). Rubric version: cv-rubric-v1.0. See docs/ for the rubric.

## Try the rules engine
    pip install -r requirements.txt
    python -m core.engine path/to/cv.pdf internship     # target: internship, scholarship, "graduate study", leadership, or leave off
    python -m tests.test_smoke

## Layout
- core/rubric.py   weights, bands, word lists (change numbers here, bump the version)
- core/reader.py   PDF and DOCX reading, clear errors
- core/checker.py  the one shared checker that finds the facts
- core/rules.py    rules-only scoring, fixes, rewrites
- core/engine.py   file in, report out
