# CV That Works: Final Rubric, Version 1

Rubric version stamp: `cv-rubric-v1.0`
Status: ready to lock. Every score, band and rule below is what the code will use in step 2.

## 1. Categories (100 points)

| Category | Pts | Rules part | Judged part (AI judge, later trained model) |
|---|---|---|---|
| Evidence and numbers | 20 | Share of bullets with a number sets the range | Picks the score inside the range (defensible, clear numbers) |
| Bullet quality | 20 | Action-verb starts, weak phrases, scope and result pattern | Quality of each bullet |
| Sections present | 15 | All of it (headings, order) | None |
| Opening summary | 10 | Present, length, goal named, one proof point | Quality of the summary |
| Contact and first impression | 10 | All of it | None |
| Language and voice | 10 | 5 pts: clichés and tense | 5 pts: typos and overall voice |
| Format and length | 10 | 8 pts: page count, bullets vs paragraphs | 2 pts: date and font consistency, only where the file shows it |
| Fit to goal | 5 | Keyword check against the chosen target | Fit judgement |

No target chosen: drop Fit to goal. Final = raw out of 95 x 100 / 95, rounded to a whole number.

## 2. Rules-only scoring (what the tool uses when the AI judge is down)

**Evidence and numbers (20).** Share of bullets with a number, scale or result:
| Share | Range | Rules-only score |
|---|---|---|
| 70% or more | 16 to 20 | 16 + 4 x ((share - 70) / 30) |
| 40% to 69% | 10 to 15 | 10 + 5 x ((share - 40) / 30) |
| 15% to 39% | 5 to 9 | 5 + 4 x ((share - 15) / 25) |
| Under 15% | 0 to 4 | 4 x (share / 15) |

**Bullet quality (20).** Action verb start 8 (share of bullets starting with a strong verb x 8). Weak phrases ("responsible for", "helped with", "assisted in", "worked on", "duties included") 6 (lose 1.5 per weak phrase, floor 0). Scope and result pattern 6 (share of bullets that have a verb plus a number or named outcome x 6).

**Sections present (15).** Points as in `03_rubric_updates.md`. Experience and Leadership or volunteering count as a pair worth 4: the better of the two earns the full 4 if it has at least 2 real bullets, a half-filled one earns 2. Order check deducts up to 2 (contact first 1, summary next 0.5, education and projects above experience for a student 0.5). Languages: detected, never scored.

**Opening summary (10).** Present 4. Length of 2 to 3 lines (25 to 60 words) 2. Goal or target named 2. One proof point (a number or named achievement) 2. A cliché in the summary costs 1.

**Contact and first impression (10).**
| Item | Pts | Full marks when |
|---|---|---|
| Email | 3 | Name-based, no casual words or nicknames, no long digit strings. 1 pt if working but casual |
| LinkedIn | 3 | Custom link, `linkedin.com/in/` plus a readable name. 1 pt if present but ends in random digits |
| Phone | 2 | Valid Nigerian or international format |
| City | 2 | City or city and state/country found near the top |

**Language and voice (10).** Rules part 5: lose 1 per cliché phrase found (max 4), lose 1 for a tense switch inside one role (current role in present tense, past roles in past tense). Judged part 5: typos and voice. Rules-only: judged part is scored as 3 of 5 (neutral) and the screen says it was not checked by the AI.

**Format and length (10).** Pages: 1 to 2 pages = 4, 3 pages = 2, more than 3 or no text = 0. Bullets vs paragraphs: bullets for 80% or more of lines = 4, 50 to 79% = 2, under 50% = 0. Judged part 2: date and font consistency. Rules-only: date format consistency check (one date style throughout) = 2, else 0.

**Fit to goal (5).** Keyword lists per target (internship, scholarship, graduate study, leadership). Matches found / matches expected x 5, capped at 5. "Not sure" counts as no target.

## 3. Short first CV protection
- A CV with fewer than 6 bullets is scored on the bullets it has. Missing bullets are not double-penalised in Evidence and Bullet quality. The fix list says "add more bullets under Projects or Volunteering".
- No work experience costs nothing if Leadership or volunteering is strong (pair rule above).
- No length penalty below 1 page.

## 4. Blending (locked)
- Facts (page count, email, LinkedIn, phone, city, headings, numbers found, clichés): rules decide.
- Judged items: AI judge and trained model decide, rules act as a check.
- Two voters: average. Three voters: middle value.
- **Disagreement gap: more than 30% of the points of the judged item.** Examples: Bullet quality (20) gap is 6 points. Evidence (20) gap is 6. Opening summary (10) gap is 3. Language judged part (5) gap is 1.5. Fit to goal (5) gap is 1.5.
- When the gap is exceeded: use the middle value (or the average with two voters), mark "less certain", and queue the CV for trainer review (consent only, redacted text only).
- Split categories (Language, Format, Evidence): the rules part is fixed. Only the judged part is blended and gap-checked.
- Evidence: the judge may move the score only inside the range the rules set.
- AI judge unavailable: rules-only score, screen says so.
- Total = sum of blended categories, rescaled if no target. The band comes from the total.
- Repeat-run rule (tested in step 8): the same CV scored three times stays within one band.

## 5. Bands
| Score | Band |
|---|---|
| 85 to 100 | Ready |
| 70 to 84 | Nearly |
| 50 to 69 | Needs work |
| Below 50 | Rebuild (go back to Build mode) |

Band is shown biggest. The number sits below with the line "This score is approximate".

## 6. Result screen fields (order on screen)
1. Band (large), total score, score per category.
2. Banner if rules-only ("Checked by rules only. AI check was not available").
3. Three things working, each with the reason.
4. Top three fixes in priority order, each with points gained.
5. Missing sections.
6. Rewrites of the two weakest bullets with [__] placeholders. No invented numbers.
7. One next step.
8. Fixed line: "Keep only numbers you can defend in an interview."
9. "Less certain" note on any category where voters disagreed.
10. On re-upload: previous score next to the new one.

## 7. Blurred-distinction flags (checked by the judge, listed by rules where words appear)
Cumulative vs yearly, participant vs leader, prototype vs deployed, ongoing vs completed, team vs individual result, registered vs informal group, undergraduates vs graduates. Trigger words for rules: "led" and "organised" next to "attended" or "participated", "deployed" or "launched" next to "prototype" or "mockup", "over the year" or "total" next to a number.

## 8. Defaults confirmed
One link, no login. 3 uploads per device per day. Show total, band and all category scores. Consent tickbox saves redacted text only. Target dropdown: internship, scholarship, graduate study, leadership, not sure.
