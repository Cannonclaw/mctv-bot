# Supabase Edge Functions

Source of record for the edge functions behind the public pages. These are
**not** deployed by Render — same deal as the `scripts/0NN_*.sql` migrations,
they are applied by hand:

```
supabase functions deploy contract-initiate --project-ref dtapevlfnekzepbtlabj
```

(or paste the file into the Supabase dashboard → Edge Functions). Deploying is
what makes a change here live; merging the PR only version-controls it.

| Function | Called by | Writes |
|---|---|---|
| `contract-initiate` | `static/rates.html` — Accept → sign → submit | `contract_requests` (truth), `quote_submissions`, `leads`, `pipeline_opportunities`, `tasks`, `activity_log` |
| `quote-submit` | `static/rates.html` — Decline | `quote_submissions` |

Only `contract-initiate` is checked in so far. It was pulled from the live
deployment and this copy matches what is deployed — verify with
`get_edge_function` / the dashboard if in doubt, and redeploy after editing.

## Things that bite

- **`leads` requires `industry` and `contact_phone`** (both `NOT NULL`). The
  agreement modal collects neither reliably — phone is optional and there is no
  industry field at all — so both are sent as `''`, the way the intake form
  writes a skipped field. A `null` fails the insert, and because that write is
  best-effort the failure is silent: the signer lands in `contract_requests`
  and never reaches the leads inbox.
- **`activity_log.entity_id` is a `uuid`, not the ref.** It takes the
  `contract_requests` row id; the human-readable `SSA-…` ref goes in `details`.
  Passing the ref there fails the insert on a type error — silently, same
  best-effort reason.
- **Only the `contract_requests` insert throws.** Everything after it is
  best-effort by design, so the client still sees a confirmation when a
  downstream write fails. Check `activity_log.details` for `lead_insert_error`.
- **A tripped honeypot is stored, not dropped.** The hidden `company_website`
  field lands the row as `status='spam'` with a note, and the function stops
  before leads/pipeline/tasks. It used to return `{ok:true}` and write nothing,
  which loses a real signature outright if a browser autofills the field — the
  client sees "You're on the board!" and no record exists anywhere. Check
  `contract_requests` for `status='spam'` before assuming a client never
  submitted. The response is deliberately identical to a clean one, so a bot
  learns nothing.
- **Throttle is 5/hr per email and 8/hr per IP.** A room full of people on one
  venue WiFi shares an IP, so the 9th signer at an event gets a 429. The
  calculator now shows the server's actual message, so that reads as
  "Too many requests — please call us" rather than a network error.
