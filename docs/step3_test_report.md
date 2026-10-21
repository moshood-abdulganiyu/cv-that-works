# Step 3 Test Report: rules engine calibration (rubric cv-rubric-v1.0, rules-only, target: internship)

## Ladder of 8 fictional CVs (each rung keeps the flaws above it and adds more)
| Rung | Planted flaw added | Score | Band |
|---|---|---|---|
| R8 | None (strong reference) | 97 | Ready |
| R7 | Casual email, no LinkedIn | 92 | Ready |
| R6 | Numbers removed from 3 bullets | 85 | Ready |
| R5 | Cliché summary | 75 | Nearly |
| R4 | "Responsible for" and "Helped with" bullets, awards, certifications and languages removed | 56 | Needs work |
| R3 | All numbers removed from bullets | 48 | Rebuild |
| R2 | Projects, leadership and phone removed | 40 | Rebuild |
| R1 | Fictional weak CV (all planted mistakes) | 34 | Rebuild |

Result: order is strictly correct, every band appears, strong lands at 97 (target near 90), weak at 34 to 40 (target near 40). Repeat runs give identical scores.

## Trainer CVs (reference points, kept off GitHub)
| CV | Score | Band | Main reasons |
|---|---|---|---|
| Full CV, 3 pages | 76 | Nearly | 50% of bullets carry a number, no city, 3 pages, mixed date styles |
| Simplified beginner CV, 2 pages | 87 | Ready | 3 unfilled placeholders, 2 phone digits masked as XXX, numbers in about 66% of bullets |

## Parsing problems found on real PDFs and fixed
Hyperlinked LinkedIn (URL stored under the word), dashes glued to the first word, lone bullet glyphs, bullets glued to the line before, role headers marked with a bullet, section titles with extra words, wrong city taken from the skills line, tense check mixing headers across roles.

## Added without changing the rubric
A notice (no points) when a CV still has unfilled [ ] placeholders.

## Known limits (to check with real student CVs in later steps)
- The ladder is built from one fictional base, so it proves ordering, not variety. Real student CVs will be tested at step 8 and used at step 9.
- Page count for DOCX is estimated from word count.
- Two-column or table-heavy CV designs may read in a mixed order.
- Rules cannot see typos, voice quality or whether numbers are real. That is the AI judge's job in phase 2.
- Strong CVs cannot pass 97 in rules-only mode because the judged parts use neutral fallbacks.
