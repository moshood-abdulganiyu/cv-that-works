# CV That Works: CV scoring tool

[![Live site](https://img.shields.io/badge/live-cv--that--works.vercel.app-1f4a80)](https://cv-that-works.vercel.app)

A free web tool for first-time CVs, built for Brainstorm Group (BSG) CV training. An undergraduate uploads a CV (PDF or DOCX), picks a target, and gets a score out of 100, a band, what is working, and the top fixes. It supports the session "CV That Works".

**Live site:** https://cv-that-works.vercel.app

Everything is free to run: Vercel free plan, Gemini free tier, Upstash free plan. The Vercel free plan is for non-commercial use, which fits a free class. If the class ever becomes paid, revisit hosting.

## Contents
- [Current status](#current-status)
- [What a student sees](#what-a-student-sees)
- [Scoring](#scoring-rubric-cv-rubric-v10)
- [How the voters work](#how-the-voters-work)
- [Privacy](#privacy)
- [Layout](#layout)
- [API](#api)
- [Settings](#settings-vercel-settings-environment-variables)
- [Trainer review page](#trainer-review-page)
- [Training the model (step 9)](#training-the-model-step-9)
- [Run and test locally](#run-and-test-locally)
- [Deploy](#deploy)
- [Free-tier limits](#free-tier-limits-checked-october-2026-re-check-before-a-class-pilot)
- [Roadmap](#roadmap)
- [Rules for the build](#rules-for-the-build)

## Current status
- **Live and open to students** with two voters: the rules code and the Gemini AI judge, blended into one score.
- **Upload limit:** 7 per device per day while the class uses it (the code default is 3, set in Vercel).
- **One list of advice:** the rules and the AI no longer give two separate fix lists. They are merged into one (see [Advice merge](#advice-merge)).
- **Third voter (trained model):** not added yet. It needs real CVs that the trainer has corrected, and the evaluation notebook refuses to recommend a model below 50 corrected CVs. Treat anything under about 100 as an experiment. Training on made-up CVs is not allowed.
- **Data keeps arriving:** students who tick the optional save box add redacted CVs to the review store, ready for the trainer to correct.

## What a student sees
- **Upload page:** file, target (internship, scholarship, graduate study, leadership, not sure), a consent tickbox, an optional save tickbox, one "Score my CV" button. The button stays grey until a file is chosen and the consent box is ticked. A strip below shows how the 100 points are split.
- **Result screen:** total score, band, score for each category, three things working, top three fixes with the points each would gain, missing sections, rewrites of the two weakest bullets with [__] placeholders, what the AI reader liked, questions about lines that could be read two ways, one next step, and a line saying only numbers the student can defend should stay on the CV.
- **Light and dark mode:** a button in the top bar switches between them. The choice is remembered on that device, and the first visit follows the phone's own setting. The logo switches with the mode.
- **Re-upload** shows the previous score next to the new one.
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

### Advice merge
The scores come from the blend above. The advice (fixes and rewrites) is merged separately in `core/blend.py` so students see one list, not two that sometimes disagree.

| Part | Who writes it |
|---|---|
| Fixes for contact, sections, format, numbers and language | Rules. The AI cannot see contact details and does not count |
| Fixes for bullets, summary and fit | AI, when it gave a fix for that category. Otherwise the rules fix stays |
| Rewrites of the weakest bullets | AI, when it gave any. Otherwise the rules rewrites stay |
| Points gain on each fix | Rules fixes: exact. AI fixes: an estimate (room left in the category, shared between its fixes, capped at 4) |

The AI labels each fix with the category it improves. A fix without a valid label is ignored by the merge. If the AI is unavailable, students get the rules fixes and rewrites unchanged. Merging never changes the scores.

A third voter, a small model trained on real CVs the trainer has corrected, is planned for phase 3. It will take the middle value of the three. It is never trained on made-up CVs.

## Privacy
- Uploaded files are read in memory, scored and deleted. Nothing is written to disk.
- Before anything goes to the AI, name, email, phone, links and address lines are removed. School, clubs and town stay in the text, and the consent line says so. Free AI services may keep the text and let people at the provider read it.
- Nothing about a student is saved unless they tick the optional save box. Then only the redacted text, scores and the AI's output are stored, with no name, email, phone, links or file.
- Never ask for or keep ID numbers, passwords or a home address.
- Never commit student CVs, exports from the review page, API keys or the review code to GitHub.
- The browser remembers the student's light or dark mode choice and, for the current session, their last score. Both stay on the student's own device. Nothing is sent to the server.

## Layout
```
app.py                Vercel entrypoint (plain WSGI). Routes: POST /api/score, GET /api/health, GET /, GET /review, /api/review/*
core/rubric.py        weights, bands, word lists (change numbers here, bump the version)
core/reader.py        PDF and DOCX reading, clear errors, reads link addresses, repairs glued dates
core/checker.py       the one shared checker that finds the facts
core/rules.py         rules-only scoring, fixes, rewrites, flags
core/redact.py        removes name, email, phone, links, handles, address lines before the AI sees text
core/judge.py         Gemini judge: prompt, call, answer checks (fixes carry a category label), backup model, fallback
core/blend.py         blends rules and judge into one score per category, marks "less certain", merges the advice
core/review.py        review store (Upstash), saving with consent, trainer endpoints
core/engine.py        file in, report out
core/service.py       multipart reading, consent, save box, per-device limits (Upstash), privacy strip
public/index.html     student upload page and result screen (markup and JavaScript)
public/style.css      page styles (design from the Google Stitch export)
public/light-mode-logo.jpg   Brainstorm Group (BSG) logo for light mode, fixed at the top-left
public/dark-mode-logo.jpg    Brainstorm Group (BSG) logo for dark mode
public/review.html    trainer review page (needs the review code)
train/                evaluation notebook for step 9. export.json and model_v1.json stay private (see .gitignore)
tests/                ladder.py (builds the calibration CVs), test_smoke, test_api, test_no_summary,
                      test_judge, test_blend, test_merge, test_review, test_routes, repeat_run
docs/                 rubric_v1.md, step3_test_report.md, step4_deploy.md
vercel.json           excludes tests and docs from the deployed function
requirements.txt      pypdf, python-docx (runtime only)
requirements-dev.txt  adds reportlab (tests)
```
Fonts (Inter, Plus Jakarta Sans and Playfair Display for the title) load from Google Fonts. Icons are built into the page, so there is no icon font to download.

## API
**Score:** `POST /api/score`, multipart, same origin. Fields: `file` (PDF or DOCX, max 4 MB), `target`, `consent` (`true`), `save` (`on`, optional). Success: `{"ok": true, "result": {...}, "uploads_left_today": 4, "stored": false}`. `stored` is true only when the CV really reached the review store.

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
| `UPLOADS_PER_DEVICE_PER_DAY`, `UPLOADS_PER_IP_PER_DAY` | Upload limits (code defaults 3 and 30; live value for the class: 7 per device) |
| `LIMIT_SALT` | Optional. Salt for the hashed limit counters |

New variables only apply on the next deployment, so push a change after editing them. An empty commit works: `git commit --allow-empty -m "apply settings"` then `git push`.

## Trainer review page
Open `/review` and enter the review code. CVs the two readers disagreed on come first. Type your own score for each category, save, and download your corrections as JSON for training (step 9). Delete a CV from the same page. Mark by your own judgment, not by copying the tool's numbers, or the model will only learn the tool's habits. Do not correct non-undergraduate CVs: the export contains corrected CVs only.

## Training the model (step 9)
Work on your own computer, never in a hosted notebook, because the export holds students' redacted CVs.

1. Correct saved CVs at `/review` until you have enough. Under 50 the notebook will say "do not add". Around 100 is where a model becomes worth trusting.
2. Download the export from `/api/review/export` and save it as `train/export.json`. It is git-ignored.
3. Install once: `pip install jupyter pandas scikit-learn numpy`.
4. Run `jupyter notebook`, open the notebook in `train/`, and run each cell from the top.
5. The notebook rebuilds the rules counts with the same `core/checker.py` the live tool uses, tests a small model against simple guesses on CVs it never saw (average, rules-only, blended), and prints a verdict. It saves `train/model_v1.json` only if the verdict is to add the model.

The model scores judged items only (bullets, summary, language, fit). If it does not beat the simple guesses, it is not added.

## Run and test locally
```
pip install -r requirements-dev.txt
python -m tests.test_smoke
python -m tests.test_no_summary
python -m tests.test_judge
python -m tests.test_blend
python -m tests.test_merge
python -m tests.test_review
python -m tests.test_routes
python -m tests.test_api
python -m tests.repeat_run     (needs a real Gemini key in that window only, about 5 minutes)
```
Score one file from the command line: `python -m core.engine path\to\cv.pdf internship`

Re-run the calibration tests after any change to `core/checker.py`, `core/reader.py` or `core/rubric.py`.

## Deploy
Vercel deploys on every push to `main`.
```
git add -A
git commit -m "describe the change"
git push
```
The "Redeploy" button rebuilds the old commit, so push a change instead. After a deploy, check `/api/health`: `review_database` and `review_code_set` should both be `true`, and `/style.css` should load.

## Free-tier limits (checked October 2026, re-check before a class pilot)
- Vercel Hobby: free, non-commercial. Confirm the function-call limit on the Usage page.
- Upstash free: 256 MB and 500,000 commands a month. About 6 commands per score and about 3 more per saved CV.
- Gemini free: Flash-Lite about 10 requests a minute and 500 a day per project. Free-tier prompts may be used by Google and read by reviewers. When a busy class hits the limit, students get the rules-only score and the screen says so.

## Roadmap
| Phase | Steps | Status |
|---|---|---|
| 1 Rules-only tool | 1 to 6 | Done and live |
| 2 AI judge | 7 AI judge, 8 blending and review | Done and live |
| 3 Trained model | 9 collect corrected CVs and train | In progress: collecting data, notebook ready |
| 3 Trained model | 10 add the model as the third voter, weak-spots view | Not started |

## Rules for the build
- Never invent metrics, dates, roles or skills. Use [__] placeholders.
- Flag blurred distinctions: cumulative vs yearly, participant vs leader, prototype vs deployed, ongoing vs completed, team vs individual, registered vs informal group, undergraduates vs graduates.
- Only numbers a student can defend should stay on a CV, and the screen says so.
- The tool must always return a result, with the rules-only score as the fallback.
- Train only on real CVs the trainer has corrected.
