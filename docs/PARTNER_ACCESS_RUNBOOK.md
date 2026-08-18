# Partner Evaluation Access — Runbook

How to give an outside organization (NTV360, another franchise, a prospective
licensee) a look at the portal without handing over the product.

---

## Before you issue anything

These are gates, not suggestions. Work top to bottom.

| # | Step | Why it's first |
|---|------|----------------|
| 1 | **File the copyright registration** (~$65, steps in `IP_PROTECTION_GUIDE.md`) | Registration *before* infringement is what unlocks statutory damages and attorney's fees. Its value drops sharply the day after you disclose. |
| 2 | **Get the NDA + Evaluation Agreement signed** | Must include confidentiality, scope of use, no reverse engineering, no derivative works, **non-circumvention**, no onward disclosure to franchisees, term, audit right, survival. The non-circumvention clause is the one that matters — a plain NDA doesn't stop someone building their own version from ideas. |
| 3 | **Rebuild `TRADE_SECRETS.md`** (gitignored, currently missing) | The DTSA and Miss. Code Ann. 75-26-1 require you to show *reasonable measures* to keep secrets secret. The registry, the NDA, and the controls below are those measures. |

The in-app terms in `pages/portal_partner_terms.py` **supplement** a signed
agreement. They do not replace one.

---

## Issuing access

Apply the migration once:

```
scripts/024_partner_demo_access.sql   # via Supabase SQL Editor
```

Then seed the sandbox tenant:

```bash
python scripts/seed_demo_tenant.py --org "NTV360" \
    --email partner-demo@mctvofms.com --days 30
```

This creates a synthetic client (`Demo Advertiser Co.`) with fabricated
contracts, invoices, reports, and creative requests, plus a Supabase Auth user
with `role='partner'`. The generated password prints **once** and is stored
nowhere — deliver it out of band, after step 2 above.

Set `--days` to the shortest window that's actually useful. Renewing is a
conversation; open-ended access is not.

---

## What the partner can and cannot do

**Can:** browse the dashboard, contracts, invoices, reports, creative requests,
and profile pages for the synthetic tenant.

**Cannot:**

- See any real client, contract, rate, or invoice — the demo tenant is
  self-contained and `is_demo` gates the performance figures
  (`services/portal_service.py`, `_demo_live_performance`).
- See real network totals. `_compute_live_performance` reads network-wide
  NTV360 snapshots; demo sessions get synthetic numbers instead.
- Write anything. Every write path calls `assert_writable()`
  (`services/partner_access.py`), which stops the script. Hidden buttons are
  cosmetic; this is the control.
- Reach team pages. Those are behind `APP_PASSWORD`, a separate auth path.
- Reach `get_admin_summary()` (whole-book MRR) — it refuses to run inside a
  portal session.

---

## What gets recorded

Every partner session writes to `activity_log` with a real client IP:

- `portal_login` / `portal_logout`
- `portal_page_view` (one row per page per session)
- `partner_terms_accepted` (also written to `portal_terms_acceptances` with
  timestamp, IP, and user agent — this is your proof of agreement)

Documents generated while an evaluation session is active carry a provenance
line in the footer and in the file's own metadata, including a stable
per-viewer canary (`canary_token()`). A leaked document traces back to the
account that saw it — match the `ref XXXXXXXXXX` string against the audit log.

Check what they've looked at:

```sql
select action, details, ip_address, created_at
from activity_log
where client_id = '<demo client id>'
order by created_at desc;
```

---

## Revoking

```bash
python scripts/seed_demo_tenant.py --org "NTV360" --revoke
```

Sets `portal_access_expires_at` to now. Live sessions are ejected within 60
seconds — `check_portal_auth()` re-checks on a cached interval, so this does not
wait for them to log out. Demo data and the audit trail are retained.

To remove the tenant and its synthetic rows entirely:

```bash
python scripts/seed_demo_tenant.py --org "NTV360" --purge
```

The Supabase Auth user must be deleted separately in the dashboard.

Inspect at any time with `--show`.

---

## Known limits of this setup

Worth being straight about, because these are real:

- **Isolation is enforced in Python, not the database.** The portal runs on the
  Supabase service-role key (`services/supabase_client.py`), so RLS never
  evaluates. A missing `client_id` filter in new code would return everything.
  The durable fix is migrating the portal to the user's JWT + real RLS; the
  tokens are already in session state and simply unused.
- **No org/tenant boundary exists.** `clients` rows are the only isolation unit,
  so a partner cannot be given multiple scoped users.
- **`scripts/fix_rls_policies.sql` has four bugs** that would abort it the day
  RLS is switched on: `is_team_member()` is declared with no arguments but
  called as `is_team_member(auth.uid())`, and storage policies reference
  `clients.user_id`, which does not exist (the column is `portal_user_id`).
- **Token-in-URL pages** (`portal_nps`, `portal_renewal`, `portal_simulator`)
  use non-expiring share tokens and skip login entirely. Don't send those links
  to a partner.

None of this stops a determined party who simply has the idea. Obfuscation was
never the moat. What's defensible is the registered copyright, the signed
non-circumvention agreement, the client relationships, and speed. The controls
here exist to make casual copying traceable and to demonstrate reasonable
measures under the DTSA.
