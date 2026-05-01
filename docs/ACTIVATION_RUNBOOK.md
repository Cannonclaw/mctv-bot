# MCTV-Bot Activation Runbook

Everything in the `bot.mctvofms.com` codebase is shipped. These are the
last-mile config changes only you can do because they require credentials
or accounts in external services.

Total time: **5–10 minutes**.

---

## 1. Render: Sync the Blueprint (REQUIRED)

The 8 new cron jobs are declared in `render.yaml` but Render won't run them
until you trigger a Blueprint sync.

1. https://dashboard.render.com/blueprints
2. Find the `mctv-bot` blueprint, click it.
3. Click **Sync Blueprint**.
4. Confirm the new services (`mctv-weekly-pulse`, `mctv-briefing-push`,
   `mctv-qbo-reconcile`, `mctv-nps-send`, `mctv-winback`, `mctv-rep-recap`,
   `mctv-upsell-triggers`, `mctv-stalled-alerts`) — should all show as
   "to be created".
5. Click **Apply**.

---

## 2. Render Env Vars (paste these into your env group)

Open: https://dashboard.render.com/env-groups → `mctv-bot-env` → **Add**

### `BRIEFING_SMS_RECIPIENTS`

Copy/paste this exactly:

```
+16012018202,+16628015677,+16629070404
```

That's Creed, Mary Michael, Swayze — every team member listed in
`config/config.json` gets the daily briefing as an SMS. Drop any number to
opt them out.

### `SLACK_WEBHOOK_URL`

Only needed if you want the daily briefing in Slack. To create:

1. Slack workspace → click workspace name → **Settings & administration**
   → **Manage apps**
2. Search "Incoming WebHooks" → **Add to Slack**
3. Pick a channel (e.g. `#mctv-daily`) → **Add Incoming WebHooks integration**
4. Copy the **Webhook URL** (starts `https://hooks.slack.com/services/T...`)
5. Paste into Render as `SLACK_WEBHOOK_URL`

If you don't use Slack, skip this. Email + SMS still go out.

---

## 3. Calendar URLs (Cal.com or Calendly)

Activates the booking widget on `bot.mctvofms.com/portal_simulator?token=...`
share links. Without it, prospects see all the metrics but can't book a call
inline.

**Easiest path — Cal.com (free):**
1. https://cal.com/signup
2. Pick a username like `mctv-creed`, `mctv-mm`, `mctv-swayze`
3. Set up "15-min discovery call" event type
4. Connect Google Calendar / Outlook for availability
5. Copy each rep's booking URL (e.g. `https://cal.com/mctv-creed/15min`)

**Then either:**
- Send me the URLs and I'll commit them into `config/config.json`, OR
- Edit `config/config.json` yourself — find each `team[]` block and fill in
  `calendar_url`. Push to main, Render redeploys, done.

If you only want one shared URL for the whole team, set
`booking.default_calendar_url` in `config/config.json` and leave per-rep
fields blank.

---

## 4. (Already done — for reference)

- ✅ WordPress page `/build-your-plan/` (id 7979) — embeds public simulator
- ✅ WordPress page `/apply-to-host/` (id 7980) — embeds host application
- ✅ 12 cron jobs declared in `render.yaml`
- ✅ All 14 Supabase migrations applied (001 → 017)
- ✅ Twilio A2P campaign resubmitted, `IN_PROGRESS` (TCR review pending)
- ✅ Twilio config cleaned: usecase=notifications, demo webhooks cleared

---

## 5. After activation — quick smoke tests

Once the blueprint sync completes:

1. **WordPress pages** — visit https://mctvofms.com/build-your-plan/ and
   https://mctvofms.com/apply-to-host/ in incognito. Both should iframe
   the simulator and host application respectively.
2. **Test a cron** — Render dashboard → `mctv-rep-recap` → **Trigger Run**.
   Each rep with an `email` in `config/config.json` should get a recap email
   within ~30 seconds.
3. **Test SMS briefing push** — `mctv-briefing-push` → Trigger Run. Phones
   listed in `BRIEFING_SMS_RECIPIENTS` should get a text within a minute.
4. **Test public simulator** — open `/build-your-plan/` in incognito, click
   3-4 venues on the map, fill out the form, submit. Confirm:
   - A new lead appears in `/4_Leads` on the internal portal
   - You get a notification email at any `NOTIFY_EMAILS` address
   - The "thank you" page shows a share URL the prospect can bookmark

---

## Optional — Render Personal Access Token

If you ever want me to manage Render env vars or trigger deploys directly
(without you needing to use the dashboard), generate a PAT:

1. https://dashboard.render.com/u/settings#api-keys
2. **Create API Key** → name it `MCTV Bot Automation`
3. Copy the token (starts `rnd_`)
4. Send it to me — I'll add it to `.env` as `RENDER_API_KEY` and from then on
   any env var changes happen via API.

Not required for anything we've shipped. Just convenience.
