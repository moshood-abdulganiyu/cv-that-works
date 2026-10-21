# Step 4: Back end, deploy and test

## What the API does
`POST /api/score` (form fields: `file`, `target`, `consent`) and `GET /api/health`.
- Refuses to run unless `consent` is true. Phase 1 stores nothing about the student, whatever the box says.
- File is read in memory, scored, then dropped. Nothing is written to disk or logged.
- Max file 4 MB (Vercel's request limit is 4.5 MB, checked Oct 2026).
- Limits: 3 scores per device per day, 30 per IP per day (a class often shares one connection). Only successful scores count, so a bad file does not use up an upload. Day resets at midnight Lagos time.
- Response never includes `facts` (email, phone). Stray emails or phones in quoted bullets show as [email] and [phone].
- Errors come back as `{"ok": false, "error": {"code", "message"}}`. Codes: `missing_consent`, `no_file`, `too_large`, `empty_file`, `locked_pdf`, `corrupt`, `scanned_pdf`, `unsupported_type`, `limit_reached`, `server_error`.
- If the counter store is down, scoring still works (the tool must always return a result).

## Connect to Vercel (about 10 minutes)
1. Copy the new files over your repo folder, run `python -m tests.test_api`, then commit and push to GitHub.
2. Vercel dashboard, **Add New, Project**, pick the GitHub repo, **Import**. Leave Framework as "Other". Click **Deploy**.
3. Add the counter store: open the project, **Storage** tab, choose **Upstash Redis** from the Marketplace, pick the **Free** plan, connect it to this project (all environments). Vercel adds the connection variables for you.
4. Project **Settings, Environment Variables**: add `LIMIT_SALT` with any long random text. Optional: `UPLOADS_PER_DEVICE_PER_DAY` (default 3) and `UPLOADS_PER_IP_PER_DAY` (default 30).
5. **Deployments**, open the latest, **Redeploy** so the new variables apply.
6. Upstash free plan is 500,000 commands a month. Each score uses about 6, so about 80,000 scores a month. Re-check before launch.

## Test the live link (replace YOUR-APP)
```
curl https://YOUR-APP.vercel.app/api/health
```
Should show `"limit_store": "upstash"`. If it says memory, step 3 or 5 is not done.
```
curl -i -c jar.txt -b jar.txt -F "file=@mycv.pdf" -F "target=internship" -F "consent=true" https://YOUR-APP.vercel.app/api/score
curl -F "file=@mycv.pdf" https://YOUR-APP.vercel.app/api/score          # expect missing_consent
```
Run the first command 4 times: the 4th should return `limit_reached`. If curl shows a Vercel login page, open Settings, Deployment Protection and switch off Vercel Authentication for production.

## Known limits to keep in mind
- A student who clears cookies gets a fresh device counter, but the IP cap still applies.
- Counters hold hashed keys only, no CV content.
