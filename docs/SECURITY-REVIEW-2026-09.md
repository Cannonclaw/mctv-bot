# Credential & Secret Handling Review — September 2026

Scope: how this codebase stores, transmits, logs and gates credentials.

Method: eight independent audit passes over the repository, each finding then put to three adversarial reviewers (accuracy, reachability, impact) who were instructed to refute it. Only findings a majority could not refute are listed. 4 further findings were raised and refuted; they are not reproduced here.

**44 findings confirmed — 12 fixed in this change, 32 still open.**

## Act on these first

Three credentials must be rotated by hand. Code changes cannot do it, and for the two committed ones neither can rewriting git history — every existing clone and fork already has them.

1. **Portal account passwords.** One password was committed in `scripts/setup_portal.py` and provisioned all three team portal accounts (two admin, one sales_rep). It has been in the repo since commit `18c0153`. Reset all three in Supabase Auth.

2. **The `test@mctvofms.com` portal password**, committed in `scripts/setup_test_client.py`. That account is auto-allowlisted because it holds a `portal_user_id`, so it is a live login, not a fixture.

3. **The Explee AutoGTM API key** (`sk_explee_…`) shared in chat during this review. Delete and recreate it in the Explee dashboard. It is unrelated to this repo — no code here uses it.

## Fixed in this change

| Sev | Location | Finding |
|---|---|---|
| critical | `scripts/integration_test.py:70` | Owner's live portal password hardcoded in scripts/integration_test.py |
| high | `pages/0_Intake.py:320` | Public intake logo upload writes to an attacker-chosen path (traversal via business name) |
| high | `scripts/setup_portal.py:37` | Hardcoded shared password creates three real portal admin accounts and is printed to the console |
| high | `services/auth.py:45` | Login lockout lives in st.session_state, so the shared team password can be brute-forced without limit |
| medium | `pages/3_Settings.py:77` | Save API Key truncates .env, destroying every other secret in the file |
| medium | `scripts/setup_test_client.py:43` | Production portal password hardcoded in a tracked script; the account it creates is auto-allowlisted |
| medium | `services/notification_service.py:77` | SMTP credentials sent over TLS with certificate verification disabled |
| low | `.gitignore:8` | .gitignore misses three runtime data dirs — SMS consent + message bodies and full pipeline deals are git-trackable |
| low | `services/supabase_client.py:594` | Capability tokens are written into stdout logs on any Supabase error path |
| info | `.dockerignore:3` | .dockerignore excludes .env but not config/qb_tokens.json or data/, so COPY . . can bake QuickBooks OAuth tokens into an image layer |
| info | `services/quickbooks_service.py:65` | QuickBooks token file is gitignored but not dockerignored, and is written world-readable |
| info | `services/supabase_client.py:565` | Supabase REST error handler logs the full untruncated PostgREST error body |

## Open — not addressed here

These are verified defects outside the credential-handling scope of this branch. The RLS ones change a live database and the repo's convention is that migrations are applied by hand in the Supabase SQL editor, so they are reported rather than shipped.

| Sev | Location | Finding |
|---|---|---|
| high | `pages/0_Hosts.py:265` | Anonymous public forms flip any phone number to SMS opted-in, overwriting a prior opt-out |
| high | `scripts/008_pipeline_schema.sql:86` | Pipeline RLS policies are missing `TO service_role`, so anon has full CRUD on every deal and contact |
| medium | `pages/0_Hosts.py:247` | Host application is silently discarded on a Supabase write failure while the visitor sees a success page and the team is emailed "Lead landed in the Host Pipeline" |
| medium | `pages/0_Hosts.py:236` | Host form collects SMS consent but persists no proof of it — client_ip is computed and thrown away |
| medium | `pages/0_Intake.py:367` | Anonymous intake submission silently re-opts-in any phone number, reversing a prior STOP |
| medium | `pages/3_Settings.py:32` | QuickBooks OAuth state is generated but never validated, so the stored connection can be swapped by CSRF |
| medium | `pages/Plan.py:362` | Public /Plan page records SMS consent for any unverified phone number and overwrites prior opt-outs |
| medium | `scripts/004_lead_followup_log.sql:41` | CREATE POLICY IF NOT EXISTS is invalid PostgreSQL — migrations 004 and 005 abort entirely |
| medium | `scripts/012_referrals_table.sql:7` | referrals created with no RLS — referred-contact PII and referral codes open to the anon key |
| medium | `scripts/014_nps_surveys.sql:7` | nps_responses created with no RLS — survey_token is the auth for the public NPS page |
| medium | `scripts/025_venue_events.sql:82` | TO authenticated USING (true) exposes internal data to portal clients, who hold authenticated JWTs |
| medium | `scripts/fix_rls_policies.sql:114` | profiles_own_update lets a portal client set their own role, unlocking all 45 is_team_member() policies |
| medium | `server_routes.py:117` | /board/events.json caches on an unvalidated venue param and fires up to 8 unbounded table reads per miss |
| medium | `services/briefing_service.py:660` | Anonymous business name from /Plan is interpolated unescaped into the daily briefing HTML email |
| medium | `services/contract_service.py:852` | Renewal token is permanent, unrevocable, and lets any link-holder mint a real contract |
| medium | `services/simulator_service.py:483` | Simulator share link ignores the expires_at its own schema defines — the 90-day link is permanent |
| medium | `services/sms_service.py:171` | set_consent can never reach its local fallback and reports success for a failed write, including opt-outs |
| medium | `services/web_scraper.py:429` | Scraper fetches any URL from a prospect's page, including file:// — arbitrary local file read and internal-network SSRF |
| medium | `supabase/functions/contract-initiate/index.ts:52` | Throttle on the service-role endpoint is keyed on a client-supplied X-Forwarded-For hop |
| medium | `supabase/functions/contract-initiate/index.ts:98` | Signature record's only attribution fields are attacker-supplied, and the same value poisons activity_log.ip_address |
| low | `pages/Plan.py:345` | TCPA consent IP is taken from the client-controlled leftmost X-Forwarded-For hop |
| low | `requirements.txt:1` | requirements.txt pins no upper bound on streamlit while the app monkeypatches five private Streamlit internals |
| low | `scripts/002_contract_alerts_log.sql:22` | contract_alerts_log policy omits TO service_role, granting anon full CRUD |
| low | `scripts/018_commission_tracking.sql:12` | commission_payouts created with no RLS — per-rep pay and per-client rates open to the anon key |
| low | `services/auth.py:193` | Portal sessions never expire or revalidate — revoked accounts keep full access |
| low | `services/nps_service.py:111` | NPS survey token never expires and submit_response has no server-side single-use guard |
| low | `services/quickbooks_service.py:88` | QuickBooks refresh-token rotation is lost or goes stale: ephemeral local file is preferred over the durable store |
| low | `services/referral_service.py:61` | Public intake page does a service-role `select=*` on the clients table from a URL parameter |
| low | `services/task_service.py:45` | Service-role key is spelled two ways and five modules silently fall back to the anon key |
| low | `static/service-worker.js:91` | Root-scoped service worker caches every successful same-origin GET with no expiry or logout invalidation |
| low | `supabase/functions/contract-initiate/index.ts:147` | Edge function writes pipeline_opportunities directly, bypassing the create_opportunity() name gate and landing in every revenue statistic |
| low | `supabase/functions/contract-initiate/index.ts:159` | tasks dedup key is a server-minted random ref, so the documented idempotency never applies and a client retry double-writes every table |

## Open findings in detail

### `pages/0_Hosts.py:265` — Anonymous public forms flip any phone number to SMS opted-in, overwriting a prior opt-out

**Severity:** high · **Category:** consent-record-tampering

pages/0_Hosts.py:265 and pages/Plan.py:362 are reachable with no authentication (neither file calls check_password/check_team_auth/require_portal_auth) and both call sms_service.set_consent(phone, opted_in=True) with a phone number typed by the visitor. set_consent (services/sms_service.py:158-186) does an unconditional upsert — it never reads the existing opted_in value, so an existing record with opted_in=False is overwritten with True. There is no phone-ownership check anywhere (no OTP, no callback), so the submitter need not own the number. check_consent (sms_service.py:189-196) reads that same row and is the only gate send_sms applies (sms_service.py:285-291), so flipping the row re-arms the app to text that number. The only way an opt-out is ever recorded in this codebase is a team member choosing "Opt Out" in pages/12_Messaging.py:308-309 — there is no inbound STOP webhook anywhere in the repo (grep for STOP finds only outbound copy), so verbal/email opt-outs recorded by a rep have no carrier-level backstop at all.

**Impact.** Someone who asked a rep to stop texting (recorded via 12_Messaging.py "Opt Out") is silently re-opted-in by anyone who submits their number on https://mctv-bot.onrender.com/0_Hosts or /Plan — including the person themselves by accident, a competitor, or a bot. The app then treats them as consenting and send_sms will dispatch to them. Twilio's own STOP list only blocks numbers that texted STOP to the Twilio number (error 21610, documented at sms_service.py:52); a rep-recorded opt-out has no such protection, so those messages go out. Each such message is an independent TCPA claim, and the consent row the company would produce as its defense was written by the complainant's attacker.

**Suggested fix.** In set_consent, refuse to upgrade False -> True from an unauthenticated caller: add an `allow_reverse: bool = False` parameter, read `existing[0].get('opted_in')` first, and when it is explicitly False and allow_reverse is not set, leave the row alone and record the attempted re-opt-in for review. Pass allow_reverse=True only from pages/12_Messaging.py where a team member is acting. Better, gate the public forms behind a confirmation SMS (send one message with bypass_consent=True and only set opted_in=True on a START/YES reply).

### `scripts/008_pipeline_schema.sql:86` — Pipeline RLS policies are missing `TO service_role`, so anon has full CRUD on every deal and contact

**Severity:** high · **Category:** rls-anon-exposure

Both policies on `pipeline_opportunities` and `pipeline_activity` are named "service_role_*" and commented "Service role has full access", but neither has a `TO service_role` clause. A Postgres policy with no role clause applies to PUBLIC — which includes `anon` and `authenticated`. With `USING (true) WITH CHECK (true)` on `FOR ALL`, any holder of the project's anon key can SELECT, INSERT, UPDATE and DELETE the entire sales and host pipeline. The same omission repeats in scripts/002_contract_alerts_log.sql:22, scripts/004_lead_followup_log.sql:41 and scripts/005_ntv360_snapshots.sql:45. The later migrations got it right (scripts/020_tasks.sql:40, scripts/024_screen_inventory.sql:70, scripts/025_venue_events.sql:79 all say `FOR ALL TO service_role`), which is what makes 008 an outlier rather than a house style.

**Impact.** Anyone holding the Supabase anon key (a key whose whole purpose is to be handed to browsers, and which any portal client or former team member can retain) can GET /rest/v1/pipeline_opportunities?select=* and pull every prospect and client business name, contact name, email, phone, monthly_value, notes and rep attribution for the whole book of business — then DELETE or rewrite it, since the same policy grants writes. The anon key is not currently shipped to any browser in this repo (static/rates.html posts to edge functions without it), which is the only thing keeping this off `critical`.

**Suggested fix.** Add `TO service_role` to both policies (`CREATE POLICY "service_role_pipeline" ON pipeline_opportunities FOR ALL TO service_role USING (true) WITH CHECK (true);`) and apply the same fix to 002_contract_alerts_log.sql, 004_lead_followup_log.sql and 005_ntv360_snapshots.sql. Then audit the live database with `SELECT tablename, policyname, roles FROM pg_policies WHERE schemaname='public'` and drop any policy whose roles column shows `{public}`.

### `pages/0_Hosts.py:247` — Host application is silently discarded on a Supabase write failure while the visitor sees a success page and the team is emailed "Lead landed in the Host Pipeline"

**Severity:** medium · **Category:** silent-write-loss

pages/0_Hosts.py:247 writes the host application with supabase_client.insert_row() instead of pipeline_service.create_opportunity(). insert_row returns None on any failure — _rest_request catches urllib.error.HTTPError, prints, and returns None (services/supabase_client.py:559-566), and also returns None when SUPABASE_URL/keys are unset (supabase_client.py:534-547). The return value is assigned to `opp` at line 247 and never read again (grep for `opp` in the file matches only line 247). Execution falls straight through to line 302-303, which sets host_app_submitted and reruns into the "Thanks — we got your application" screen. This is exactly the failure mode CLAUDE.md says was fixed: create_opportunity routes through _sb_request(..., raise_on_error=_sb_configured()) (services/pipeline_service.py:279-280) so a configured-but-failing write raises PipelineWriteError instead of vanishing. Going around it also skips the FOLLOW_UP_SLA next_action_date (pipeline_service.py:272-275) and the 'created' pipeline_activity row (pipeline_service.py:282), so even a successful insert produces a deal with no scheduled follow-up and no activity history.

**Impact.** Any RLS change, unmigrated column, expired service key, or Supabase outage causes every host venue application to be dropped on the floor. The applicant is told it succeeded, and the team receives an email that explicitly asserts the lead is in the Host Pipeline at stage 'identified' — so nobody checks. The only trace is a print line in the Render log. Inbound host venues are the acquisition channel for the 125-screen network; a week of this loses every applicant with no way to recover their details.

**Suggested fix.** Replace the direct insert_row call with pipeline_service.create_opportunity(), which already validates the name, sets the SLA follow-up, logs activity, and raises PipelineWriteError on a configured-but-failing write. Wrap it in try/except and, on failure, show the visitor an error with a phone number instead of the success screen, and send the team notification with a subject that says the write failed so the lead can be re-keyed by hand.

### `pages/0_Hosts.py:236` — Host form collects SMS consent but persists no proof of it — client_ip is computed and thrown away

**Severity:** medium · **Category:** missing-consent-proof

pages/0_Hosts.py:236-245 copies the proof-of-consent IP capture block verbatim from pages/0_Intake.py:326-335 (where it carries the comment "Capture client IP (best-effort) for proof-of-consent") but the resulting `client_ip` is never referenced again — the insert_row payload at lines 247-260 contains no consent fields, and pipeline_opportunities has no consent columns (scripts/008_pipeline_schema.sql:6-41, scripts/013_pipeline_deal_type.sql, scripts/023 enrichment migration — no sms_consent* column in any of them). The only artifact left behind is the set_consent row, and scripts/fix_rls_policies.sql:560-566 shows sms_consent has exactly four columns: phone, opted_in, name, updated_at. So the exact checkbox text agreed to (SMS_CONSENT_LABEL, pages/0_Hosts.py:184-188), the URL, the timestamp of the agreement, and the IP are all discarded. By contrast pages/0_Intake.py:351-356 and pages/Plan.py:343-347 persist sms_consent, sms_consent_at, sms_consent_ip, sms_consent_text and sms_consent_url onto the leads row (columns added by scripts/009_sms_consent_columns.sql).

**Impact.** Host venues are texted on the strength of a checkbox whose agreement the company cannot evidence. When a host applicant files a TCPA complaint or Twilio/TCR requests opt-in proof during an A2P 10DLC audit, the only record retrievable for that number is {phone, opted_in:true, name, updated_at} — no disclosure text, no URL, no IP, and a timestamp that any later re-submission overwrites. Statutory TCPA damages are $500-$1500 per message, and the dead client_ip line makes the code read as though proof is being kept.

**Suggested fix.** Add sms_consent, sms_consent_at, sms_consent_ip, sms_consent_text and sms_consent_url to the insert payload (shipping the pipeline_opportunities migration first, per the CLAUDE.md rule), or add those columns to the sms_consent table and extend set_consent to accept and store them so every public form's proof lands in one place. Either way, stop computing client_ip and discarding it.

### `pages/0_Intake.py:367` — Anonymous intake submission silently re-opts-in any phone number, reversing a prior STOP

**Severity:** medium · **Category:** consent-integrity

The unauthenticated intake form calls set_consent(phone, opted_in=True) with whatever phone number was typed. set_consent looks up an existing sms_consent row for that number and overwrites it with opted_in=True — it never checks whether the number previously opted out, and there is no verification that the submitter controls the number and no throttle on the page at all (the sibling self-serve endpoint in supabase/functions/contract-initiate/index.ts:56-70 does have per-email and per-IP throttling; this page has none). The "proof of consent" IP stored alongside it is the leftmost value of the client-supplied X-Forwarded-For header, which any submitter can set.

**Impact.** Someone who replied STOP has opted_in flipped back to True by any anonymous form submission naming their number; services/sms_service.py:287 (`if not bypass_consent and not check_consent(to_formatted)`) is the only gate on outbound SMS, so the team's next campaign texts them again — a TCPA violation the stored record will appear to authorize. The same lack of throttling lets one script create unlimited leads, consent rows and SMTP notification sends, and the sms_consent_ip kept as proof is whatever X-Forwarded-For the submitter chose.

**Suggested fix.** In set_consent, never downgrade a standing opt-out from an unverified source: read the existing row and refuse to move opted_in False→True unless the caller passes an explicit verified/team flag. For the IP, take the last (proxy-appended) X-Forwarded-For entry rather than the first, or read the peer address, and add per-IP/per-phone throttling plus a honeypot field to pages/0_Intake.py the way contract-initiate already does.

### `pages/3_Settings.py:32` — QuickBooks OAuth state is generated but never validated, so the stored connection can be swapped by CSRF

**Severity:** medium · **Category:** auth-bypass

The page generates a CSRF state with secrets.token_hex(16) and puts it in the authorization URL (lines 301-305), reads the returned state into _qb_state at line 32 — and then never compares the two. Neither the automatic redirect handler (lines 34-44) nor the paste-the-callback-URL handler (lines 320-338, which does not even parse `state`) checks it. grep for qb_oauth_state across the repo returns only the three lines that create and send it.

**Impact.** A logged-in team member who follows a link to https://bot.mctvofms.com/Settings?code=<attacker-code>&realmId=<attacker-realm> causes exchange_code() to run unprompted on page load and _save_tokens() to overwrite the stored MCTV tokens with tokens for the attacker's QuickBooks company — in both config/qb_tokens.json and the app_settings row. Every later sync then runs against the attacker's realm: sync_all_clients() (pages/3_Settings.py:267) pushes the full MCTV client list, names, emails and invoice amounts into a QuickBooks company the attacker controls, and payment reconciliation silently reports nothing owed. Nothing in the UI reveals the swap beyond a changed Realm ID.

**Suggested fix.** Compare the returned state to st.session_state.qb_oauth_state before calling exchange_code in both handlers, abort with an error when it does not match, and clear the stored state after a successful exchange so a code cannot be replayed. Generate the state unconditionally at the top of the page rather than inside the not-connected branch, so it exists when the redirect lands.

### `pages/Plan.py:362` — Public /Plan page records SMS consent for any unverified phone number and overwrites prior opt-outs

**Severity:** medium · **Category:** unauthenticated-privilege-grant

pages/Plan.py has no auth (module docstring line 6: 'No auth'), and its form handler calls set_consent(p_phone, opted_in=True) with a phone number typed by an anonymous visitor. The only validation is the >=10-digit check at line 303-304 — no OTP, no ownership proof, no rate limit. services/sms_service.py:174-178 then UPDATEs an existing sms_consent row rather than refusing, so a number the team previously set to opted_in=False (via pages/12_Messaging.py:309) is silently flipped back to opted-in. The same pattern exists on the other two public forms, pages/0_Intake.py:367 and pages/0_Hosts.py:265.

**Impact.** check_consent() is the sole gate on every outbound message (send_sms, sms_service.py:287) and on the bulk sends in pages/12_Messaging.py:160/237. Anyone on the internet can submit the public planner with a third party's number and that number becomes textable by the team; worse, a number the team manually opted out after a phone or email complaint (not a carrier STOP, which Twilio blocks with 21610) is restored to opted-in by one anonymous form post, so the next campaign texts someone who explicitly asked not to be. The consent proof captured on the lead (sms_consent_ip / _text / _url, Plan.py:344-347) is not copied into sms_consent, so the record that actually authorizes sending carries no evidence at all.

**Suggested fix.** Do not flip an existing opted_in=False record from a public form — have set_consent() refuse to upgrade a prior opt-out without an authenticated caller. Carry the consent IP, timestamp, text and URL into the sms_consent row so the sending gate holds the proof, and rate-limit consent writes per IP on the public pages.

### `scripts/004_lead_followup_log.sql:41` — CREATE POLICY IF NOT EXISTS is invalid PostgreSQL — migrations 004 and 005 abort entirely

**Severity:** medium · **Category:** broken-migration

PostgreSQL's CREATE POLICY grammar has no `IF NOT EXISTS` variant (unlike CREATE TABLE/INDEX/TRIGGER). Both scripts/004_lead_followup_log.sql:41 and scripts/005_ntv360_snapshots.sql:45 use it. Each file's header instructs the operator to paste the whole thing into the Supabase SQL Editor, which sends it as one simple-query string: the parse error on the final statement rejects the entire batch before anything executes, so the CREATE TABLE, the indexes, the trigger and the ENABLE ROW LEVEL SECURITY all roll back too. Neither table is created by any other migration — I grepped all 28 .sql files.

**Impact.** If the files were run as documented, `lead_followup_log` and `ntv360_snapshots` do not exist. services/supabase_client.py:_rest_request turns the resulting HTTP error into None and lead_followups.py returns `{}`, so every cron run reads "no welcome email sent yet" and re-mails the same leads indefinitely; services/ntv360_service.py:83 upserts silently fail, so monthly traction reports fall back to total_plays=0 — precisely the bug migration 005 was written to fix. If instead the statements were run one at a time, the two tables sit with RLS enabled and zero policies (fail-closed, works via the service key) — but nobody can tell which state production is in, because the intended policy never applied in either case.

**Suggested fix.** Replace both statements with `DROP POLICY IF EXISTS "<name>" ON <table>; CREATE POLICY <name> ON <table> FOR ALL TO service_role USING (true) WITH CHECK (true);` — the drop-then-create idiom already used in scripts/024_screen_inventory.sql:68-70. Then verify in the SQL editor that both tables actually exist before trusting the follow-up and snapshot crons.

### `scripts/012_referrals_table.sql:7` — referrals created with no RLS — referred-contact PII and referral codes open to the anon key

**Severity:** medium · **Category:** missing-rls

Migration 012 creates `referrals` and ends at line 48 with COMMENTs. There is no `ENABLE ROW LEVEL SECURITY` and no policy in this or any other .sql file. The table holds third-party PII collected from hosts — `referred_contact_name`, `referred_contact_email`, `referred_business_name` (lines 14-16) — plus `referrer_code`, which is the value the /Intake?ref=<code> deep link trusts for attribution (line 39).

**Impact.** An anon-key read dumps the contact name, email and business of every person a host venue referred — people who never transacted with MCTV and never consented to having their details in a queryable public endpoint. Anon writes can also forge rows (`status='converted'`, `reward_value`) against any `referrer_code` harvested from the same table, manufacturing referral credit, or wipe the referral ledger that services/referral_service.py pays out from.

**Suggested fix.** Add `ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;` plus a `FOR ALL TO service_role USING (true) WITH CHECK (true)` policy, matching scripts/025_venue_events.sql:77-79.

### `scripts/014_nps_surveys.sql:7` — nps_responses created with no RLS — survey_token is the auth for the public NPS page

**Severity:** medium · **Category:** missing-rls

Migration 014 creates `nps_responses` and stops at a COMMENT on line 33. There is no `ALTER TABLE nps_responses ENABLE ROW LEVEL SECURITY` and no policy — I grepped every .sql in scripts/ and the table appears in no other file. No GRANT/REVOKE exists anywhere in the repo either, so Supabase's default `public` schema grants to `anon`/`authenticated` stand and PostgREST exposes the table for unrestricted CRUD. The table stores `survey_token` (line 13), which is the *only* credential for the public page: pages/portal_nps.py:49-56 reads `?token=` and calls `find_survey_by_token(token)` with no other check.

**Impact.** Anyone holding the project's anon key can `GET /rest/v1/nps_responses?select=survey_token,client_id` and harvest every live survey token, then open /portal_nps?token=<uuid> as any client and submit or overwrite their NPS answer — the token is the entire auth. The same read returns every client's verbatim `what_working` / `what_not_working` and their score, and anon UPDATE/DELETE can rewrite or wipe the NPS history that pages/21_RepDashboard.py and services/nps_service.py report on. Compare migration 022 (app_settings), which deliberately relies on "RLS on, no policies" — that fail-closed posture is exactly what is missing here.

**Suggested fix.** Add `ALTER TABLE nps_responses ENABLE ROW LEVEL SECURITY;` plus `CREATE POLICY nps_responses_service_all ON nps_responses FOR ALL TO service_role USING (true) WITH CHECK (true);` — the pattern already used in scripts/024_screen_inventory.sql:66-70. All reads go through services/nps_service.py with the service key, so nothing in the app breaks. Rotate outstanding survey_tokens after applying.

### `scripts/025_venue_events.sql:82` — TO authenticated USING (true) exposes internal data to portal clients, who hold authenticated JWTs

**Severity:** medium · **Category:** role-conflation

Three migrations grant blanket SELECT to the `authenticated` role on the assumption that it means "team member": venue_events (025:81-83), loop_items (024:72-74) and tasks (020:42-43, commented "all team members see all tasks"). It does not. services/auth.py:96-103 adds every client with a `portal_user_id` to the portal allowlist, and those advertisers and hosts are real Supabase Auth users — auth.py:232-235 stores the `access_token` their sign-in returns, whose role is `authenticated`. Migration 025's own comment on lines 73-76 refuses an anon policy because it would leak "private titles and internal notes", then hands the identical read to every client account on line 82.

**Impact.** A host venue's portal account, using its own credential against the project's REST endpoint, can read `venue_events` in full — the unmasked titles of competing venues' private bookings and their `internal_note` column, the exact data services/venue_events_service.mask() strips on the public board. The same credential reads `loop_items.monthly_value` and `advertiser`, i.e. what every other advertiser on the network pays, and the full internal `tasks` list with its descriptions and related_customer_id. The masking at the service layer is defeated by reading the table directly.

**Suggested fix.** Drop the three `*_select_authenticated` policies (025:81-83, 024:72-74, 020:42-43). Every read in the app already goes through the service key — services/supabase_client.py:query_table defaults `use_service_key=True` — so removing them changes no app behavior. If team-only read access is wanted later, gate it on a claim that distinguishes staff from portal clients rather than on the bare `authenticated` role.

### `scripts/fix_rls_policies.sql:114` — profiles_own_update lets a portal client set their own role, unlocking all 45 is_team_member() policies

**Severity:** medium · **Category:** privilege-escalation

The policy comment says "name, phone, company — not role", but the policy only constrains which ROW may be updated (`id = auth.uid()`), never which COLUMNS. An authenticated portal user can therefore PATCH their own profiles row and set `role` to `admin`. `public.is_team_member()` (lines 60-71 of the same file) resolves team membership by reading exactly that column, and 45 separate policies in this file are gated on nothing but `is_team_member()` — including leads_team_select, clients_team_select, and the contract and invoice team policies. The same unrestricted policy exists in scripts/setup_portal_schema.sql:202. The app compounds it: services/supabase_client.py:165-172 (sign_in) and the identical block in verify_otp read `profiles.role` into the session, and pages/portal_dashboard.py:43 turns that into `is_admin`.

**Impact.** An advertiser or host with a working portal login (magic link or the temp password emailed at onboarding) sends one PATCH to /rest/v1/profiles?id=eq.<their uid> with {"role":"admin"} using the anon key and their own JWT. From that moment is_team_member() is true for them, and every team-scoped policy in fix_rls_policies.sql opens: the full leads table, every other client's record, every contract and invoice. Their next portal login also comes back with role='admin', so pages/portal_dashboard.py treats them as staff.

**Suggested fix.** Restrict the writable columns: drop profiles_own_update and replace it with a policy whose WITH CHECK pins the privileged columns, e.g. `WITH CHECK (id = auth.uid() AND role = (SELECT role FROM public.profiles WHERE id = auth.uid()))`, or revoke UPDATE on profiles.role from `authenticated` with a column-level GRANT and let only the service key change roles. Apply the same change to scripts/setup_portal_schema.sql:202.

### `server_routes.py:117` — /board/events.json caches on an unvalidated venue param and fires up to 8 unbounded table reads per miss

**Severity:** medium · **Category:** resource-exhaustion

The public JSON feed takes the `venue` query parameter, lowercases it, and uses it directly as a key into a module-level dict that is never bounded or evicted. The value is also never checked against BOARD_VENUES — venue_config() (venue_events_service.py:81-91) deliberately accepts any slug — so every distinct string an attacker sends is a cache miss that reaches Supabase. On a miss, board_payload() runs day_schedule() once for today and then, because an unknown venue has no live events, again for each of LOOKAHEAD_DAYS, and each of those calls _fetch(), which issues a fresh REST GET with no `limit` and filters the day window in Python.

**Impact.** Anyone with the board URL loops `GET /board/events.json?venue=<random>`; each request permanently adds an entry to _data_cache (never evicted, key length bounded only by the proxy's URL limit) and issues 8 Supabase REST calls, each with a 15s urllib timeout. Because the handler runs _resolve through asyncio.to_thread, those 8 blocking calls occupy a worker from the default executor (min(32, cpu+4) — roughly 5 threads on the Render starter plan), so a few concurrent requests stall /rates, /board and /mdot as well as the feed, while the lobby screens fall back to the stale marker. Memory grows until the container is OOM-restarted.

**Suggested fix.** Reject unknown venues at the route: `if venue and venue not in BOARD_VENUES: return 404` (keep the lenient venue_config() fallback for internal callers only), which bounds _data_cache to the known slugs. Pass a bounded window to the query itself — add `starts_at=gte.<midnight>&starts_at=lt.<midnight+8d>` and a `limit` to _fetch — and fetch the today+lookahead range once instead of calling day_schedule eight times.

### `services/briefing_service.py:660` — Anonymous business name from /Plan is interpolated unescaped into the daily briefing HTML email

**Severity:** medium · **Category:** html-injection

pages/Plan.py is ungated and its `p_business` field (Plan.py:271) goes through save_lead (Plan.py:350, services/leads_service.py:71-88) into the leads table with no validation at all — unlike pages/0_Hosts.py, Plan.py never calls validate_business_name. build_briefing then reads every lead (services/briefing_service.py:128) and the HTML renderer interpolates business_name straight into the message body with an f-string at services/briefing_service.py:660 and :674 — there is no html.escape anywhere in the file. The body is attached as text/html (briefing_service.py:862) and mailed to NOTIFY_EMAILS by the mctv-daily-briefing Render cron (render.yaml:28-32, scripts/daily_briefing.py). Reaching the rendered "Hot Leads" block is not incidental: Plan.py:333 hardcodes interest_level to "Ready to go — let's get started", which calculate_lead_score turns into a +15 bonus (services/leads_service.py:189-191), and get_score_label calls >=70 Hot (leads_service.py:246-247).

**Impact.** Anyone on the internet submits the /Plan form with a business name such as `Acme</td></tr><tr><td><a href="https://mctv-invoices.example/pay">URGENT: unpaid invoice, click to settle</a>` and that markup is rendered inside the next morning's briefing email — a message the sales team trusts because it arrives daily from portal@mctvofms.com. Mail clients block scripts, but attacker-chosen links, hidden text and fake table rows all render, giving an unauthenticated outsider a way to plant phishing links inside a trusted internal email and to corrupt the layout of the report the team runs its day on.

**Suggested fix.** Escape every externally-sourced string on the way into the HTML: import html and wrap the interpolations at briefing_service.py:660, :674 and :572 (invoice business_name) with html.escape(...). Add the same treatment to the contract title at :615. A length cap on business_name in save_lead is worth adding too, but escaping at the render site is the fix that covers all public write paths.

### `services/contract_service.py:852` — Renewal token is permanent, unrevocable, and lets any link-holder mint a real contract

**Severity:** medium · **Category:** token-lifetime

find_contract_by_renewal_token() (line 826-831) filters only on renewal_token — no status, no expiry, no acceptance check. accept_renewal_offer() then calls renew_contract(), which calls create_contract() (line 88-148) and inserts a real contracts row with the original's tier, screen_count and monthly_rate copied over, then stamps renewal_accepted_at on the original. scripts/011_renewal_token_columns.sql:7-11 adds no expiry column at all, and renewal_offer_sent_at is only ever written (contract_service.py:811, 815) — `grep -rn renewal_offer_sent_at --include=*.py` shows zero reads. Nothing anywhere in the repo ever sets renewal_token back to NULL, so there is no revocation path. The link also renders tier, screen count, monthly rate and markets to whoever opens it (pages/portal_renewal.py:106-114).

**Impact.** A renewal email sent at the 30-day mark (scripts/contract_alerts.py:245-248) stays a live, binding capability forever. If the client forwards it, it sits in a shared inbox, or the contract is later cancelled or manually renewed by a rep, anyone who still has the URL can click Renew and the app creates a new contracts row for that client with copied pricing and stamps renewal_accepted_at. The team has no way to invalidate a leaked link — there is no revoke code path, and the only "expiry" message on pages/portal_renewal.py:58 is a lie, because the lookup never expires anything.

**Suggested fix.** Add a renewal_offer_expires_at column (or bound on renewal_offer_sent_at) and have find_contract_by_renewal_token() reject expired tokens; reject tokens whose contract status is not 'active'/'expired'; and NULL renewal_token in accept_renewal_offer() after a successful accept so the capability is single-use. Add a Contracts-page control that NULLs renewal_token to revoke a leaked link.

### `services/simulator_service.py:483` — Simulator share link ignores the expires_at its own schema defines — the 90-day link is permanent

**Severity:** medium · **Category:** token-lifetime

scripts/migrate_simulator_tables.sql:30 declares `expires_at TIMESTAMPTZ DEFAULT (now() + INTERVAL '90 days')`, but load_scenario_by_token() filters on share_token alone and never reads expires_at. `grep -rn expires_at --include=*.py .` returns no hits anywhere in the repo, so nothing enforces it. There is likewise no code that rotates or clears share_token after insert, so there is no revocation path.

**Impact.** A share link handed to a prospect keeps working indefinitely, and pages/portal_simulator.py:124-132 and 239-248 render the quoted monthly rate, the effective (possibly discounted) rate, the CPM, and the full named venue/screen-count list for that package. A link forwarded to a competitor, left in a lost deal's email thread, or held by a departed rep still exposes MCTV's pricing and venue-level network breakdown years later, and the page at line 74 tells the reader the link 'has expired' only when the token is wrong — never when it is old.

**Suggested fix.** Add `&expires_at=gt.<now>` to the lookup (or filter in Python after the fetch) and return None for expired scenarios; add a way to clear/rotate share_token from pages/16_Simulator.py so a leaked link can be killed.

### `services/sms_service.py:171` — set_consent can never reach its local fallback and reports success for a failed write, including opt-outs

**Severity:** medium · **Category:** silent-write-loss

set_consent wraps its Supabase path in try/except and falls back to local JSON on exception (services/sms_service.py:171-186). But none of query_table, insert_row or update_row ever raises: query_table returns [] when _rest_request returns None (services/supabase_client.py:605-606), and insert_row/update_row return None (supabase_client.py:609-614, 667-674), because _rest_request swallows HTTPError and every other exception and returns None (supabase_client.py:559-569). So on an HTTP 400/401/403 the try block completes normally and hits the bare `return` at line 179 — the local fallback at 183-186 is unreachable whenever supabase_client imports, and set_consent's None return tells the caller nothing. Every caller then reports success: pages/12_Messaging.py:309-311 prints st.success(f"{name} opted out") unconditionally, and the public pages' `except Exception` handlers (pages/0_Hosts.py:266-267, pages/Plan.py:363-364) can never fire.

**Impact.** The compliance-critical direction fails silently: a rep records "Opt Out" for a customer who asked to stop being texted, Supabase rejects the write (RLS policy change, key rotation, outage), the UI says the number is opted out, and the row still reads opted_in=true — so check_consent keeps returning True and send_sms keeps texting them. The same silence loses opt-in proof written from the three public forms. Nothing is logged on the app side; the only trace is a print in the Render container log.

**Suggested fix.** Make set_consent return a bool: capture the result of update_row/insert_row, treat None as failure, write the local JSON fallback on failure instead of only on exception, and return False. Then have pages/12_Messaging.py:309 and the public forms branch on it — st.error on a failed opt-out rather than st.success, and raise/alert on a failed opt-in so consent is never assumed.

### `services/web_scraper.py:429` — Scraper fetches any URL from a prospect's page, including file:// — arbitrary local file read and internal-network SSRF

**Severity:** medium · **Category:** ssrf

`download_image()` hands an attacker-controlled string straight to `urllib.request.urlopen` with no scheme allowlist and no host validation. The only filter is `_is_valid_image()`, which accepts any URL whose lowercased text merely contains "image", "photo" or "upload" (line 511-517) — and `urllib.request.Request` strips the `#fragment` before opening the file, so `file:///proc/self/environ#upload` passes the filter and is then read off disk. I verified the full chain in this checkout: `_is_valid_image("file:///.../t.txt#upload")` returns True and `download_image()` returned a temp path holding the file's 4000 bytes. The URLs come from `<img src=...>` on the scanned site via `urljoin` (line 293-296), which preserves an absolute `file:` URL. The same lack of validation applies to `scrape_website_text()` (line 32) and `_fetch_html()` (line 117), which additionally follow HTTP redirects with no re-check of the destination, so a prospect URL can be bounced to any internal or link-local address. The CLAUDE.md claim that scraped photos are opt-in does not hold: `auto_assign_photos()` (line 701-758) sets `default_placement` on up to 11 images and `pages/1_Proposals.py:424-425` uses it as the selectbox default, so a single click on "Download Selected Images" fetches them.

**Impact.** A rep pastes a prospect's website into Proposals > "Scan Website for Images" (or Pipeline > enrichment) — routine work, and the site may simply be compromised. The page serves <img src="file:///proc/self/environ#upload">, and the container reads its own environment block — SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY, TWILIO_AUTH_TOKEN, SMTP_PASS, APP_PASSWORD — into a temp file that is then embedded into the generated proposal. The http(s) variant is worse for read-back: `enrich_from_website()` feeds the fetched body to Claude and stores the result in the deal's `description`, so the contents of any internal or link-local HTTP endpoint reachable from the Render container become visible in the Pipeline UI.

**Suggested fix.** Validate before every fetch, not after: parse the URL, reject anything whose scheme is not http/https, resolve the hostname and reject loopback/private/link-local/unique-local addresses (127.0.0.0/8, 10/8, 172.16/12, 192.168/16, 169.254/16, ::1, fc00::/7), and re-run the same check on each redirect hop by installing a custom `HTTPRedirectHandler` via `build_opener` instead of relying on the default. Put the check in one helper used by `scrape_website_text`, `_fetch_html` and `download_image`, and drop the substring heuristic in `_is_valid_image` in favour of a real scheme+extension test.

### `supabase/functions/contract-initiate/index.ts:52` — Throttle on the service-role endpoint is keyed on a client-supplied X-Forwarded-For hop

**Severity:** medium · **Category:** rate-limit-bypass

The function is the only internet-exposed code that holds SUPABASE_SERVICE_ROLE_KEY (line 54), and rates.html calls it with no apikey/Authorization header (static/rates.html:1211-1214), so it is genuinely unauthenticated. Its only anti-abuse control is the 8/hr-per-IP + 5/hr-per-email throttle at lines 56-70. The IP half derives the caller from `(req.headers.get('x-forwarded-for') ?? '').split(',')[0]` — the LEFTMOST entry, which is whatever the client wrote into the header; proxies append the real peer to the right. The email half is keyed on `contact_email`, another attacker-chosen body field. Both halves are therefore attacker-controlled, and `if (ip)` means the IP count is skipped entirely when the header is absent.

**Impact.** Anyone can rotate `X-Forwarded-For: 10.0.0.<n>` and `contact_email` per request and write unlimited rows, at service-role privilege, into contract_requests, quote_submissions, leads, pipeline_opportunities, tasks and activity_log — six production CRM tables with no other gate (the honeypot at line 25 is a hidden form field a scripted client simply omits). The same header also works in reverse: submitting 5 requests carrying a real prospect's address burns that prospect's 5/hr email quota, so their genuine signature returns 429 and rates.html:1257 tells them "Your signature was NOT recorded."

**Suggested fix.** Stop trusting the header's leftmost hop. On Supabase Edge Functions take the connection's remote address from `Deno.serve`'s second `info` argument (`info.remoteAddr.hostname`), or the rightmost X-Forwarded-For hop appended by the platform, and use that for both the `client_ip` column and the throttle lookup. Treat the missing-IP case as throttled rather than unlimited, and add a real gate (Turnstile/hCaptcha or an emailed confirmation token) since the email half of the counter can never be an abuse control.

### `supabase/functions/contract-initiate/index.ts:98` — Signature record's only attribution fields are attacker-supplied, and the same value poisons activity_log.ip_address

**Severity:** medium · **Category:** audit-integrity

contract_requests is described in the file header and README as the "record of truth" for a signed self-serve agreement, and the only attribution it keeps is `signed_name` (body field), `client_ip` (line 98) and `user_agent` (line 53) — all three chosen by the caller, with no email confirmation, OTP, or any other proof the signer controls contact_email. The same spoofable `ip` is written to activity_log.ip_address on both the spam path (line 110) and the success path (line 185); activity_log.ip_address is `TEXT` (scripts/setup_portal_schema.sql:189), so any string is stored verbatim rather than rejected as a malformed address.

**Impact.** A third party can POST a fully-formed "signed agreement" naming any local business, any contact email, any signer, and any IP they choose. The row that results is the artifact the team relies on to show a client agreed (this app elsewhere leans on Mississippi UETA click-to-sign), yet it corroborates nothing and can be made to point at an innocent IP address. The app-wide audit trail in activity_log inherits the same forged value, so incident review of this flow — the one flow where the IP is retained as evidence — reads attacker-authored data.

**Suggested fix.** Record the platform-observed remote address (see the X-Forwarded-For finding) instead of the header, and do not treat the row as a signature until the address is proven: insert it as `status='pending_confirmation'`, email a single-use confirmation link to contact_email, and only promote it to 'new' (and only then create the lead, deal and task) when that link is followed.

### `pages/Plan.py:345` — TCPA consent IP is taken from the client-controlled leftmost X-Forwarded-For hop

**Severity:** low · **Category:** forgeable-audit-record

All three public forms build the proof-of-consent IP from headers.get("X-Forwarded-For", "").split(",")[0] — pages/Plan.py:319-322 (stored as sms_consent_ip at :345), pages/0_Intake.py:329-333 (stored at :354), and pages/0_Hosts.py:239-243. The leftmost XFF entry is whatever the client sent; Render appends the real peer address to the right-hand end of the chain rather than replacing it. A submitter who sets X-Forwarded-For: 8.8.8.8 on the request controls the value that ends up in the leads.sms_consent_ip column that scripts/009_sms_consent_columns.sql describes as the opt-in evidence.

**Impact.** The IP recorded as proof that a specific person opted in is attacker-chosen. Someone mass-submitting other people's phone numbers can stamp each record with an unrelated IP, so the audit trail actively misleads: it will point investigators at an innocent address, and it cannot be used to correlate a disputed opt-in with real traffic. It also means the field cannot support rate-limiting or abuse detection.

**Suggested fix.** Take the rightmost X-Forwarded-For entry instead of the leftmost (Render appends the true client address last), or store the full header chain verbatim so a reviewer can see every hop rather than one forgeable value. Apply the same change in all three forms and drop the unused capture in 0_Hosts.py or start persisting it.

### `requirements.txt:1` — requirements.txt pins no upper bound on streamlit while the app monkeypatches five private Streamlit internals

**Severity:** low · **Category:** unpinned-dependency

Every requirement is an open-ended `>=` and there is no lockfile, so each Render image build resolves whatever Streamlit is current. The app depends heavily on Streamlit's private internals: server_routes.py replaces streamlit.web.server.server.Server._create_app and reorders app.wildcard_router.rules by index, and wraps uvicorn.Config.__init__; app.py rewrites SAFE_APP_STATIC_FILE_EXTENSIONS on two modules, AppStaticFileHandler.set_extra_headers, and create_app_static_serving_routes. Each patch is individually try/excepted and the HTML pages degrade to /app/static/<name>.html — but server_routes.py:33-34 states in its own words that the JSON feed has no such fallback.

**Impact.** A Streamlit release that renames Server._create_app or moves the static-file modules turns five patches into logged warnings rather than errors, and the app still boots — so nothing fails the deploy. /board/events.json then returns Streamlit's app shell instead of JSON, and the lobby boards on venue walls freeze on their last good schedule with only a stale marker to show for it. Because the deploy is triggered by an unrelated push and nothing in the build goes red, the cause is several commits removed from the symptom.

**Suggested fix.** Pin streamlit to a tested compatible range (e.g. `streamlit>=1.40.0,<1.50.0`) or commit a lockfile, so a patch-breaking release is an explicit upgrade rather than a side effect of the next push to main. Separately, make scripts/route_check.py assert that /board/events.json returns application/json — the module docstring already names it as the one route with no fallback, so it is the one that needs a deploy-time check.

### `scripts/002_contract_alerts_log.sql:22` — contract_alerts_log policy omits TO service_role, granting anon full CRUD

**Severity:** low · **Category:** overbroad-rls-policy

The comment on line 18 says "service role can read/write (used by the bot backend)", but the policy created on lines 22-25 has no `TO` clause. A policy with no `TO` applies to PUBLIC, so `anon` and `authenticated` both satisfy `USING (true)` / `WITH CHECK (true)` and get full SELECT/INSERT/UPDATE/DELETE. Enabling RLS here is worse than useless — it looks like protection while granting exactly what it claims to restrict. Contrast scripts/024_screen_inventory.sql:70, which writes the same policy correctly as `FOR ALL TO service_role`.

**Impact.** Anon-key reads return `sent_to` for every alert ever dispatched — the email addresses and phone numbers of clients and team members, joined to contract ids. Because scripts/contract_alerts.py uses this table for duplicate suppression, anon INSERTs of forged (contract_id, alert_type, channel) rows silently suppress real contract-expiration alerts, and anon DELETEs cause the whole fleet to re-send alerts to clients.

**Suggested fix.** Add `TO service_role` to the policy: `CREATE POLICY contract_alerts_service_all ON contract_alerts_log FOR ALL TO service_role USING (true) WITH CHECK (true);` — drop and recreate, since ALTER POLICY cannot add a TO clause.

### `scripts/018_commission_tracking.sql:12` — commission_payouts created with no RLS — per-rep pay and per-client rates open to the anon key

**Severity:** low · **Category:** missing-rls

Migration 018 creates `commission_payouts` and ends at line 41 with a COMMENT. No `ENABLE ROW LEVEL SECURITY`, no policy, and no other migration touches the table. With Supabase's default public-schema grants (the repo contains no GRANT/REVOKE), the anon key gets full CRUD through PostgREST. The `breakdown` JSONB (line 22-23) is documented as holding `{contract_id, client_name, monthly_rate, commission_rate, amount}` per contract, so the row is not just rep pay — it is a client-by-client rate card.

**Impact.** A single anon-key GET on /rest/v1/commission_payouts returns every rep's monthly compensation and, inside `breakdown`, what every named client pays per month — the most competitively sensitive data in the business. Anon UPDATE can flip `status` to 'paid' or edit `amount`, silently corrupting the payout ledger that pages/21_RepDashboard.py and services/rep_dashboard_service.py render as the source of truth for what a rep is owed.

**Suggested fix.** Add `ALTER TABLE commission_payouts ENABLE ROW LEVEL SECURITY;` and a `FOR ALL TO service_role` policy (or no policy at all, matching the app_settings pattern in scripts/022_app_settings.sql:58). Do not add an `authenticated` SELECT policy — see the role-conflation finding.

### `services/auth.py:193` — Portal sessions never expire or revalidate — revoked accounts keep full access

**Severity:** low · **Category:** session-revocation

`check_portal_auth()` decides access purely from two session-state booleans set at login time. It calls `_try_refresh_token()`, but that helper returns early when there is no refresh token, and swallows every failure in a bare `except Exception` that only prints (auth.py:218-219); a `None` return from `refresh_session` is likewise ignored. Nothing downstream depends on the Supabase token either — every portal data read goes through `query_table(..., use_service_key=True)` (services/supabase_client.py:576, default `use_service_key=True`), which bypasses RLS entirely, so authorization rests solely on the session flag. The email allowlist (`_get_allowed_portal_emails`) is checked only at login (auth.py:245, 264, 292) and never re-checked.

**Impact.** Offboarding does not work. A client whose Supabase auth user is deleted, whose password is rotated, whose sessions are revoked, or whose `clients.portal_user_id` is cleared keeps reading contracts, invoices and traction reports — and can still e-sign a contract via pages/portal_contract.py — for as long as their browser session lives, because no code path ever re-validates the token or re-checks the allowlist. There is also no absolute session lifetime, so a portal session on a shared or stolen device stays valid indefinitely.

**Suggested fix.** Make `check_portal_auth()` fail closed: have `_try_refresh_token` return a success flag, and when a refresh is attempted and fails (or `refresh_session` returns None), clear portal session state and return False. Additionally stamp a `portal_login_at` at `_set_portal_session` and force re-authentication past an absolute maximum age, and re-run `_get_allowed_portal_emails()` membership on each auth check (it is already cheap enough to cache per rerun).

### `services/nps_service.py:111` — NPS survey token never expires and submit_response has no server-side single-use guard

**Severity:** low · **Category:** token-lifetime

scripts/014_nps_surveys.sql defines survey_token with no expiry column, and find_survey_by_token() (line 95-100) filters on the token alone. submit_response() re-looks-up the row and writes the score without checking responded_at; the only 'already responded' check is the page-level one at pages/portal_nps.py:71-78, which protects the sequential double-click (the rerun re-reads the row and stops) but not two holders of the same link acting concurrently. Nothing ever clears survey_token after a response.

**Impact.** The survey link emailed by scripts/nps_send.py:89 is a permanent write capability attributed to a named client and contract. Anyone the email is forwarded to — or two people opening it at once — can submit or overwrite feedback recorded against that client, and those rows feed get_aggregate() (line 121-157), the network-wide NPS the team reports on. Because there is no expiry, a link from a contract that ended two years ago still accepts a score today.

**Suggested fix.** Add an expiry (a sent_at + N days bound checked in find_survey_by_token, or an expires_at column) and make submit_response() a no-op when responded_at is already set — ideally as a conditional PATCH filtered on `responded_at=is.null` so concurrent submits cannot both land.

### `services/quickbooks_service.py:88` — QuickBooks refresh-token rotation is lost or goes stale: ephemeral local file is preferred over the durable store

**Severity:** low · **Category:** secret-destruction

_load_tokens() returns the local config/qb_tokens.json as soon as it has an access_token and never consults Supabase again, and _save_tokens() writes that local file first while treating the Supabase write as best-effort inside a bare try/except that only prints. Intuit rotates the refresh token on every refresh_access_token() call (line 247 overwrites tokens["refresh_token"] with the new one), so the durable copy and the container-local copy drift apart.

**Impact.** render.yaml runs the web service and twelve cron jobs from the same image with no shared disk, so each container has its own qb_tokens.json. When a cron run refreshes and rotates the token, Supabase gets the new refresh token but the long-lived web container keeps returning its stale local copy from line 88 and never re-reads app_settings. The next 401 retry sends an invalidated refresh token, refresh_access_token() returns None, and the connection dies until someone re-runs the OAuth flow. Worse in the other direction: if the Supabase write at line 74/76 fails (the exact scenario scripts/022_app_settings.sql lines 9-17 was written to fix), the only copy of the newly rotated refresh token lives in a container filesystem that Render discards on the next deploy — the durable store still holds the token Intuit just invalidated, so the QuickBooks connection is permanently lost.

**Suggested fix.** Make Supabase app_settings the source of truth: read it first in _load_tokens() and use the local file only as an offline fallback, and in _save_tokens() write Supabase first and surface a failure (raise or return False) instead of printing, so a rotation that cannot be persisted is not silently accepted.

### `services/referral_service.py:61` — Public intake page does a service-role `select=*` on the clients table from a URL parameter

**Severity:** low · **Category:** key-scope

pages/0_Intake.py is the unauthenticated lead form (no check_password anywhere in the file). At line 137 it passes the visitor-supplied `?ref=` value into find_client_by_code, which queries the clients table with `select="*"`. services/supabase_client.py:573 defaults query_table to use_service_key=True, so this is a full-row, RLS-bypassing read of a host's client record — contact_email, contact_phone, notes, assigned_rep, portal_user_id — performed for an anonymous visitor, when the only field the page needs is business_name. The page then echoes that name back at line 139.

**Impact.** No column other than business_name reaches the page today, so nothing leaks yet — but the whole client row, including the host's private contact details and internal notes, is loaded into an anonymous request's memory and is one careless `st.write(_referrer)` or debug expander away from being rendered. The unthrottled response difference also turns the public form into an oracle for brute-forcing valid referral codes and confirming which businesses host MCTV screens.

**Suggested fix.** Narrow the projection to what the caller needs: `query_table("clients", select="id,business_name", filters={"referral_code": code}, limit=1)`. record_referral_signup only reads host["id"], so both call sites are satisfied by those two columns.

### `services/task_service.py:45` — Service-role key is spelled two ways and five modules silently fall back to the anon key

**Severity:** low · **Category:** key-scope

services/supabase_client.py:24 reads the service-role key from `SUPABASE_SERVICE_KEY`. Five newer modules read a different name and then fall back to the anon key when it is absent: services/task_service.py:45, services/field_notes_service.py:48, services/loop_inventory_service.py:49-50, services/rate_service.py:42 and scripts/daily_tasks.py:56 all do `os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]`. On a deployment configured per HEARTBEAT.md:164 ("Set SUPABASE_SERVICE_KEY env var on Render"), SUPABASE_SERVICE_ROLE_KEY is unset, so these five run against the anon role. The tables they touch grant nothing to anon — scripts/020_tasks.sql:40 and scripts/019_field_notes.sql:58-63 are `FOR ALL TO service_role`, and the SELECT companions are `TO authenticated` — so reads return [] and writes are rejected. The guard written to catch exactly this cannot: services/env_preflight.py:48-52 lists SUPABASE_KEY inside SUPABASE_ANY_KEY, so a cron holding only the anon key passes preflight.

**Impact.** With only SUPABASE_SERVICE_KEY set, the Tasks page and Field Notes read empty, dictated notes fail to save after the audio has already been uploaded and paid for in Claude tokens, and the mctv-daily-tasks cron emails "nothing to do" to every rep while exiting 0 — the exact silent-green failure mode env_preflight.py's docstring says cost the team weeks in August 2026. The likely field fix is worse than the bug: an operator who pastes the service-role key into SUPABASE_KEY to make Tasks work turns the variable that supabase_client.py:135-141 uses as the anon key for every /auth/v1 call into a full-privilege credential.

**Suggested fix.** Pick one name. Have all five modules call a single helper (supabase_client._get_url_and_keys or a new service_key() that checks both spellings) and raise rather than fall back to the anon key. Remove "SUPABASE_KEY" from env_preflight.SUPABASE_ANY_KEY so a cron that only has the anon key fails preflight with EX_CONFIG instead of running blind.

### `static/service-worker.js:91` — Root-scoped service worker caches every successful same-origin GET with no expiry or logout invalidation

**Severity:** low · **Category:** data-retention

services/pwa.py:82 registers static/service-worker.js with `{scope: '/'}` (and render.yaml serves it with Service-Worker-Allowed: /), and inject_pwa() runs from app.py:131 on the unauthenticated landing page, so the worker is installed for every visitor and controls the whole origin. Its default branch caches any response that is ok and same-origin into a single cache name that is only ever cleared when CACHE_NAME changes — there is no max-age, no allowlist of paths, and nothing clears it on logout.

**Impact.** On any shared or kiosk browser — the venue lobby devices and the team's shared-password logins are exactly this case — media Streamlit serves over GET during an authenticated session (report charts, uploaded client logos, /media/* assets) is written to Cache Storage and stays there after the session ends, retrievable offline by the next person on the device. cache.put also ignores Cache-Control, so the deliberate `no-store` on /board/events.json (server_routes.py:79) does not prevent the schedule from being stored.

**Suggested fix.** Restrict the caching branch to an explicit allowlist of public, static paths (/app/static/, the icons, the manifest) and let everything else fall through to the network untouched: `if (!url.pathname.startsWith('/app/static/')) return;` before the respondWith. If an offline shell is still wanted, bump CACHE_NAME on deploy and call caches.delete(CACHE_NAME) from the logout path.

### `supabase/functions/contract-initiate/index.ts:147` — Edge function writes pipeline_opportunities directly, bypassing the create_opportunity() name gate and landing in every revenue statistic

**Severity:** low · **Category:** validation-bypass

The function inserts straight into `pipeline_opportunities` with the service-role client. services/pipeline_service.py:246-253 documents create_opportunity()'s validate_business_name() call as the "backstop for every create path in the app … Enforced here so no call site can skip it" — this is a call site that skips it, because it never goes through Python. The inserted row also hard-codes `stage: 'contract_sent'` and `probability: 90` from unauthenticated input and never sets `excluded_from_stats`, so get_pipeline_summary() (services/pipeline_service.py:1219, 1237-1243) counts it in by_stage, total_pipeline_value and weighted_pipeline_value like any hand-entered deal.

**Impact.** `business_name` is only length-clipped at line 27, so exactly the junk validate_business_name() exists to reject — an email address, a URL, "Marketing Director: …", a 200-character blob — enters the pipeline from the open internet, and `monthly_total` is accepted up to 100000 (line 38). Each such POST adds up to $100,000/mo at 90% probability to the weighted forecast and to the default rep's board (assigned_rep defaults to 'Mary Michael', scripts/008_pipeline_schema.sql:29). Combined with the spoofable throttle, forecast and MRR reporting can be moved arbitrarily by an unauthenticated caller, and cleaning up requires deleting rows — which CLAUDE.md notes is the only safe removal because marking them Lost poisons win rate.

**Suggested fix.** Run the same name validation in the edge function (port validate_business_name, or reject anything containing '@', a scheme/bare domain, or a ':' label prefix), clamp/normalize before insert, and stamp the row `excluded_from_stats: true` until a human has reviewed the self-serve request — promoting it out of exclusion at countersign time — so unverified internet submissions cannot move reported revenue.

### `supabase/functions/contract-initiate/index.ts:159` — tasks dedup key is a server-minted random ref, so the documented idempotency never applies and a client retry double-writes every table

**Severity:** low · **Category:** weak-idempotency-key

The comment at line 159 claims the task insert is idempotent via `UNIQUE (source, source_id)` (scripts/020_tasks.sql:30). It cannot be: `source_id` is `ref`, minted fresh per request at lines 73-74 from a new UUID, so two POSTs of the same signature always carry different refs and always produce two rows. rates.html aborts the fetch at 20 s (static/rates.html:1209), re-enables the button and prints "Your signature was NOT recorded. Please try again" (static/rates.html:1254-1257) even though the server may have committed all six writes — the in-flight latch at line 1188 does not survive that path. Separately, `ref` carries only 4 hex characters (16 bits) of entropy per day and is used as the sole key for the final cross-row update at line 190.

**Impact.** A signer on slow venue WiFi (the exact scenario the 20 s abort was added for) clicks again and produces two contract_requests rows, two leads, two pipeline deals — double-counting their monthly value in the forecast — and two 'high' countersign tasks for Creed, with nothing in the data marking them as the same signature. On the collision side, two same-day refs make `.eq('ref', ref)` at line 190 stamp one client's opportunity_id and lead_id onto another client's request row, and the duplicate task insert fails the UNIQUE constraint silently, so the second signer gets no countersign task at all.

**Suggested fix.** Have the client mint a stable idempotency key once per agreement modal and send it in the body; use that as `tasks.source_id` and as a unique key on contract_requests, returning the existing ref on replay. Widen the random half of `ref` to at least 8 hex chars, and address the final update by the row id already in hand (`crRow.id`) rather than `.eq('ref', ref)`.

## Coverage

Audit passes: `secret-lifecycle`, `auth-controls`, `secret-leak-output`, `key-scope`, `public-surface`, `egress-and-transport`, `deploy-config`, `history-and-artifacts`.

A completeness critic then named four areas the passes had missed, which were audited in a second round: `public-token-capability-pages`, `supabase-edge-function`, `rls-in-the-other-migrations`, `other-anonymous-write-pages`.

Not covered: the live Supabase instance (no policies were queried at runtime, only the migration files), the Render dashboard configuration, and the contents of git history beyond a credential-pattern scan.

Regression tests for the fixed items: `python scripts/credential_handling_test.py`.
