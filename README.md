# CV That Works: CV scoring tool

A free web tool for first-time CVs, built for Brainstorm Group (BSG) CV training. A student uploads a CV (PDF or DOCX), picks a target, and gets a score out of 100, a band, what is working, and the top fixes. It supports the session "CV That Works".

Live site: https://cv-that-works.vercel.app

Everything is free to run: Vercel free plan, Gemini free tier, Upstash free plan. The Vercel free plan is for non-commercial use, which fits a free class. If the class ever becomes paid, revisit hosting.

## What a student sees
- Upload page: file, target (internship, scholarship, graduate study, leadership, not sure), a consent tickbox, an optional save tickbox, one "Score my CV" button.
- Result screen: total score, band, score for each category, three things working, top three fixes with the points each would gain, missing sections, rewrites of the two weakest bullets with [__] placeholders, one next step, and a line saying only numbers the student can defend should stay on the CV.
- Re-upload shows the previous score next to the new one.
- Categories where the two readers disagreed are marked "Less certain".

## Scoring (rubric `cv-rubric-v1.0`)
| Category | Points |
|---|---|
| Evidence and numbers | 20 |
| Bullet quality | 20 |
| Sections present | 15 |
| Opening summary | 10 |
| Contact and first impression | 10 |
| Language and voice | 10 |
| Format and length | 10 |
| Fit to goal | 5 |

With no target (or "not sure"), Fit to goal is dropped and the other 95 points are rescaled to 100.

| Score | Band |
|---|---|
| 85 to 100 | Ready |
| 70 to 84 | Nearly |
| 50 to 69 | Needs work |
| Below 50 | Rebuild |

The exact number is approximate. Short first CVs are not punished: missing experience costs little if projects and volunteering are well written.

## How the voters work
1. **Rules code** counts the facts (numbers in bullets, headings, email, LinkedIn, phone, city, page count, clichés, tense, weak phrases) and gives a complete score by itself.
2. **AI judge** (Gemini free tier) judges bullet quality, summary, voice and fit, and writes the comments. It returns strict JSON.
3. **Blend** (`core/blend.py`, version `blend-v1.0`) combines them per category. Rules lead on facts, the judge leads on judged items.

| Category | Blend |
|---|---|
| Evidence | Judge score, kept inside the range the rules set |
| Bullets, Summary, Fit | Average of rules and judge |
| Language | Rules part plus the judge's 0 to 5 |
| Sections, Contact, Format | Rules only |

If the two voters differ by more than 30% of a category's points, the category is marked "less certain" and the CV is queued for the trainer (only if the student ticked the save box).

If the AI is unavailable or rate limited, the student still gets the rules-only score.

A third voter, a small model trained on real CVs the trainer has corrected, is planned for phase 3. It is never trained on made-up CVs.

## Privacy
- Uploaded files are read in memory, scored and deleted. Nothing is written to disk.
- Before anything goes to the AI, name, email, phone, links and address lines are removed. School, clubs and town stay in the text, and the consent line says so. Free AI services may keep the text and let people at the provider read it.
- Nothing about a student is saved unless they tick the optional save box. Then only the redacted text, scores and the AI's output are stored, with no name, email, phone, links or file.
- Never ask for or keep ID numbers, passwords or a home address.
- Never commit student CVs, exports from the review page, API keys or the review code to GitHub.

## Layout
```
app.py                Vercel entrypoint (plain WSGI). Routes: POST /api/score, GET /api/health, GET /, GET /review, /api/review/*
core/rubric.py        weights, bands, word lists (change numbers here, bump the version)
core/reader.py        PDF and DOCX reading, clear errors, reads link addresses
core/checker.py       the one shared checker that finds the facts
core/rules.py         rules-only scoring, fixes, rewrites, flags
core/redact.py        removes name, email, phone, links, handles, address lines before the AI sees text
core/judge.py         Gemini judge: prompt, call, answer checks, backup model, fallback
core/blend.py         blends rules and judge into one score per category, marks "less certain"
core/review.py        review store (Upstash), saving with consent, trainer endpoints
core/engine.py        file in, report out
core/service.py       multipart reading, consent, save box, per-device limits (Upstash), privacy strip
public/index.html     student upload page and result screen (inline CSS and JavaScript)
public/review.html    trainer review page (needs the review code)
tests/                ladder.py (builds the calibration CVs), test_smoke, test_api, test_no_summary,
                      test_judge, test_blend, test_review, test_routes, repeat_run
docs/                 rubric_v1.md, step3_test_report.md, step4_deploy.md
vercel.json           excludes tests and docs from the deployed function
requirements.txt      pypdf, python-docx (runtime only)
requirements-dev.txt  adds reportlab (tests)
```

## API
**Score:** `POST /api/score`, multipart, same origin. Fields: `file` (PDF or DOCX, max 4 MB), `target`, `consent` (`true`), `save` (`on`, optional). Success: `{"ok": true, "result": {...}, "uploads_left_today": 2, "stored": false}`. `stored` is true only when the CV really reached the review store.

Errors: `{"ok": false, "error": {"code", "message"}}`. Codes: `missing_consent`, `no_file`, `bad_request`, `too_large`, `empty_file`, `locked_pdf`, `corrupt`, `scanned_pdf`, `unsupported_type`, `limit_reached`, `server_error`.

**Health:** `GET /api/health` shows the rubric version, file limit, upload limit, `limit_store`, `review_database` and `review_code_set`.

**Trainer endpoints** (header `X-Review-Token`): `GET /api/review/list`, `GET /api/review/item?id=`, `POST /api/review/correct`, `POST /api/review/delete`, `GET /api/review/export`.

## Settings (Vercel, Settings, Environment Variables)
| Name | What it does |
|---|---|
| `GEMINI_API_KEY` | AI judge key. Server only |
| `GEMINI_MODEL`, `GEMINI_MODEL_BACKUP` | Main and backup Gemini models. Update if a model is retired |
| `AI_JUDGE` | Set to `off` to switch the AI off |
| `REVIEW_TOKEN` | Code for the trainer page. At least 12 characters. Keep private |
| `KV_REST_API_URL`, `KV_REST_API_TOKEN` | Upstash connection (limit counters and saved CVs) |
| `UPLOADS_PER_DEVICE_PER_DAY`, `UPLOADS_PER_IP_PER_DAY` | Upload limits (default 3 and 30) |
| `LIMIT_SALT` | Optional. Salt for the hashed limit counters |

New variables only apply on the next deployment, so push a change after editing them.

## Trainer review page
Open `/review` and enter the review code. CVs the two readers disagreed on come first. Type your own score for each category, save, and download your corrections as JSON for training (step 9). Delete a CV from the same page.

## Run and test locally
```
pip install -r requirements-dev.txt
python -m tests.test_smoke
python -m tests.test_no_summary
python -m tests.test_judge
python -m tests.test_blend
python -m tests.test_review
python -m tests.test_routes
python -m tests.test_api
python -m tests.repeat_run     (needs a real Gemini key in that window only, about 5 minutes)
```
Score one file from the command line: `python -m core.engine path\to\cv.pdf internship`

## Deploy
Vercel deploys on every push to `main`.
```
git add -A
git commit -m "describe the change"
git push
```
The "Redeploy" button rebuilds the old commit, so push a change instead. After a deploy, check `/api/health`: `review_database` and `review_code_set` should both be `true`.

## Free-tier limits (checked October 2026, re-check before a class pilot)
- Vercel Hobby: free, non-commercial. Confirm the function-call limit on the Usage page.
- Upstash free: 256 MB and 500,000 commands a month. About 6 commands per score.
- Gemini free: Flash-Lite about 10 requests a minute and 500 a day per project. Free-tier prompts may be used by Google and read by reviewers.

## Roadmap
| Phase | Steps | Status |
|---|---|---|
| 1 Rules-only tool | 1 to 6 | Done and live |
| 2 AI judge | 7 AI judge, 8 blending and review | Built. Live save check being confirmed |
| 3 Trained model | 9 collect corrected CVs and train, 10 add the model as the third voter | Next |

## Rules for the build
- Never invent metrics, dates, roles or skills. Use [__] placeholders.
- Flag blurred distinctions: cumulative vs yearly, participant vs leader, prototype vs deployed, ongoing vs completed, team vs individual, registered vs informal group, undergraduates vs graduates.
- Only numbers a student can defend should stay on a CV, and the screen says so.
- The tool must always return a result, with the rules-only score as the fallback.
- Train only on real CVs the trainer has corrected.
