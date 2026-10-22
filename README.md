# CV That Works

Free CV scoring tool for first-time CVs, built for Brainstorm Group (BSG) students. A student uploads a PDF or DOCX, picks a target, ticks consent, and gets a score out of 100, a band, what is working, the top three fixes, and rewrites with [__] placeholders. Everything is free to run.

Live site: https://cv-that-works.vercel.app
Rubric version: `cv-rubric-v1.0` (see `docs/rubric_v1.md`)

## Where the build stands
| Step | What | Status |
|---|---|---|
| 1 | Lock the rubric and blending rules | Done |
| 2 | File reading and the rules engine | Done |
| 3 | Test and calibrate (ladder, weak near 40, strong near 90) | Done |
| 4 | Back end on Vercel (upload, limits, consent, delete after scoring) | Done |
| 5 | Front end (upload page, result screen, re-upload, flyer colours) | Done |
| 6 | Deploy and launch phase 1 | Done |
| 7 | AI judge (Gemini free tier), redaction, fallback | Built and sent, live check pending |
| 8 | Blend rules and judge, "less certain", trainer review queue | Next |
| 9 to 10 | Trained model as third voter, class pilot | Not started |

## How scoring works
Three voters are planned. Today two exist.
1. **Rules code** counts facts (bullets with numbers, headings, email, LinkedIn, phone, city, page count, clichés, tense, weak phrases) and gives a complete score by itself.
2. **AI judge** (Gemini free tier) judges writing quality and writes natural feedback. In step 7 it adds a separate "second opinion" section. The score still comes from the rules. Blending arrives in step 8.
3. **Trained model** (phase 3) learns only from real CVs the trainer has corrected. Never from made-up CVs.

The tool always returns a result. If the AI is busy, down or returns rubbish, the rules-only score stands and the page says so.

Bands: 85+ Ready, 70 to 84 Nearly, 50 to 69 Needs work, below 50 Rebuild. With no target the Fit points (5) are dropped and the rest is rescaled to 100.

## Layout
```
app.py              Vercel entrypoint (plain WSGI). Routes: POST /api/score, GET /api/health, GET /
core/rubric.py      weights, bands, word lists (change numbers here, bump the version)
core/reader.py      PDF and DOCX reading, clear errors, reads link addresses
core/checker.py     the one shared checker that finds the facts
core/rules.py       rules-only scoring, fixes, rewrites, flags
core/redact.py      removes name, email, phone, links, handles, address lines before the AI sees text
core/judge.py       Gemini judge: prompt, call, answer checks, backup model, fallback
core/engine.py      file in, report out
core/service.py     multipart reading, consent, per-device limits (Upstash), privacy strip
public/index.html   the whole front end (inline CSS and JavaScript)
tests/              test_smoke, test_ladder, test_api, test_no_summary, test_judge
docs/               rubric_v1.md, step3_test_report.md, step4_deploy.md
vercel.json         excludes tests and docs from the deployed function
requirements.txt    pypdf, python-docx (runtime only)
requirements-dev.txt adds reportlab (tests)
```

## Run it locally
```
pip install -r requirements-dev.txt
python -m core.engine path/to/cv.pdf internship     # target: internship, scholarship, "graduate study", leadership, or leave off
python -m tests.test_smoke
python -m tests.test_ladder
python -m tests.test_api
python -m tests.test_no_summary
python -m tests.test_judge
```
The judge test uses a pretend Gemini, so it needs no key and uses no daily allowance.

## Settings (Vercel, Project Settings, Environment Variables)
| Name | Purpose |
|---|---|
| `LIMIT_SALT` | Hashes the counter keys. Set once. Do not change later (it resets counts) |
| Upstash variables | Added by the Storage integration. Hold per-device counters only |
| `UPLOADS_PER_DEVICE_PER_DAY` | Optional, default 3 |
| `UPLOADS_PER_IP_PER_DAY` | Optional, default 30 (classes share connections) |
| `GEMINI_API_KEY` | Server only. Never put it in the page or on GitHub |
| `GEMINI_MODEL` | Currently `gemini-3.5-flash-lite` |
| `GEMINI_MODEL_BACKUP` | Currently `gemini-3.1-flash-lite`. Leave empty to disable |
| `AI_JUDGE` | Set to `off` to switch the AI check off without a code change |

A new setting only takes effect on the next deployment. Push a change to deploy. The Vercel "Redeploy" button rebuilds the old commit.

## Deploy
Local repo: `C:\Code\cv-that-works`. Vercel deploys on every push to `main`.
```
git add -A
git commit -m "describe the change"
git push
```

## Privacy
- Files are read in memory, scored and deleted. Nothing about a student is stored in phase 1 (`stored` is always false until step 8).
- Before any text goes to the outside AI, name, email, phone, links, social handles and address lines are removed. This does not make a CV anonymous: school, club, employer and town names stay. The consent line says so.
- Free-tier Gemini prompts may be used by Google to improve its products, and reviewers may read them. Staying on the free tier is the plan.
- Counters hold hashed keys only. The server logs no requests and never echoes exceptions.
- Students are advised to remove phone number and home address before upload.

## Free-tier limits (checked October 2026, re-check before relying on them)
- **Vercel Hobby:** free, non-commercial only. About 1 million function calls, 100 GB bandwidth and about 4 CPU hours a month. One source said 100,000 calls, so confirm on your own Usage page. The site pauses at a limit, it does not bill.
- **Upstash free:** 500,000 commands a month, about 6 per score.
- **Gemini free:** Flash-Lite models about 10 requests a minute and 500 a day per project, full Flash models about 20 a day. Unpublished by Google and changing. A whole class pressing the button together will hit the per-minute limit, and the extra students get the rules-only result.

## Honesty rules (built into the tool)
- Never invent metrics, dates, roles or skills. Rewrites use [__] placeholders. An AI rewrite is dropped if it adds a number the student did not write.
- Flag blurred distinctions as questions: cumulative vs yearly, participant vs leader, prototype vs deployed, ongoing vs completed, team vs individual, registered vs informal group, undergraduates vs graduates.
- The page says that only numbers a student can defend should stay on the CV.

## Troubleshooting
- **"Something went wrong on our side":** the server hides details on purpose (they could hold CV text). Reproduce locally with the same file and run `python -m core.engine file.pdf`.
- **No AI section on a result:** read the notice at the top of the result. Most likely the model name is rejected, the key is missing, or the daily AI allowance is used up. The score is still valid.
- **Page will not update after a push:** wait for the Vercel deployment to finish, then hard refresh.
- **Slow connections:** the page gives up after 60 seconds. Large files on very slow data may fail. Not yet addressed.

## Not in scope yet
Android app. Student login. Trained model. All free-tier limits and terms must be re-checked before steps 8 to 10.
