# Tupelo host audit — roster reconciliation and open items

**Prepared:** August 7, 2026
**Companion to:** [`docs/audits/tupelo-2026-08/README.md`](audits/tupelo-2026-08/README.md)

The August 4 field audit packet covers the operational side — route, labels,
capture sheet, loop overruns, missing addresses. This document covers what the
packet does not: how the packet lines up against the roster Exceed Technologies
has actually been working from since February, and what is still open from the
email thread that started the engagement.

Findings only. No Supabase records were changed.

---

## The engagement, from the email record

| Date | Event |
|---|---|
| Nov 12, 2025 | Jesse Bandre' inquires about advertising; becomes a host and partner conversation |
| Feb 17, 2026 | "JESSE/CREED CHECK IN" — Jesse asks for the **full location list**, an **audit spreadsheet template**, and Brian Miller's training availability. Says he will **propose audit pricing by territory**. |
| Feb 17, 2026 | Creed sends the Strategic Partnership Proposal (Exceed as Official Technology Partner) |
| Feb 26, 2026 | Brian Miller (NTV360) training call |
| Feb 27, 2026 | Creed sends `MCTV_Network_Audit_Workbook_1.xlsx` — 110 screens, 90 venues, 4–6 month target |
| Apr 22–24, 2026 | Tupelo Regional Airport goes live: 6 Pi licenses, Jesse is technical POC |
| Aug 4, 2026 | Field audit packet generated for Tupelo (33 screens) |

Two things from February never closed in the mail record:

- **Audit pricing by territory.** Jesse said he would propose it "shortly." No
  email in the thread shows it arriving. Six months of field work has been
  scoped without a price attached to it.
- **The 4–6 month target.** Set February 27. That window closes this month.

## Finding 1 — Exceed is holding two documents with different screen counts

The Location Roster in `MCTV_Network_Audit_Workbook_1.xlsx` is what Exceed has
been auditing from since February. For Tupelo it lists **21 screens**
(MCTV-086 … MCTV-106). The August packet says **33 screens across 27 venues**.

| | Tupelo screens |
|---|---|
| February workbook — Location Roster | 21 |
| August packet | 33 |
| Difference | **12** |

Nothing was removed — all 20 February venues still appear in the July 6 sweep.
The gap is entirely growth the roster never caught: six in-market venues added
between February and July, plus the airport's six screens in April.

If the packet goes out without the workbook being reissued, Exceed has two
authoritative-looking lists for the same market and no statement of which
supersedes which.

**Venues live today but absent from the February roster:**

| Venue | Loop | On Feb roster | Host record |
|---|---|---|---|
| Exceed Technologies | 1,199 s | ❌ | ❌ |
| Midtown Pointe Shopping Center | 958 s | ❌ | ❌ |
| VIBE Performance and Testosterone | 944 s | ❌ | ❌ |
| Pizza Doctor | 908 s | ❌ | ❌ |
| Amsterdam Deli | 744 s | ❌ | ❌ |
| Her Gym | 728 s | ❌ | ❌ |
| Tupelo Regional Airport | *special playlist* | ❌ | ❌ |

## Finding 2 — Two incompatible labeling schemes point at the same screens

This is the one that will cause confusion in the field.

**The February workbook** (Step 6 of its instructions) tells the technician to
apply a pre-assigned `MCTV-###` asset tag to every screen, and Step 5 to tag the
Pi with its license number. It ships a "Sticker & Label Specs" sheet ordering 110
of each.

**The August packet** ships 27 Avery 5163 labels carrying venue name, a short
code, the full license number, and a QR of that license number. No `MCTV-###`
anywhere.

Same screens, two label sets, two identifier systems. A technician working both
documents will either apply both and create ambiguity about which is canonical,
or apply one and leave the other's checklist columns unfillable.

**This needs a decision from MCTV before the packet ships.** Either:

- **Retire `MCTV-###`** and make the license number the single key — cleaner,
  matches how `screen_assets` import already reconciles on license number, but
  orphans the numbering in the February workbook and the 110 pre-printed tags if
  they were ordered; or
- **Keep `MCTV-###`** as the human-facing screen ID and add it to the label
  generator alongside the license QR, so one label carries both.

The second is the smaller change and preserves work already done. If that is the
call, the six unrostered venues take **MCTV-111 … MCTV-116** and the airport
takes **MCTV-117 … MCTV-122**, continuing from the roster's current end at
MCTV-110.

## Finding 3 — The packet misspelled the vendor's name *(fixed in this change)*

The generated brief, the label sheet, and the audit README all addressed
**"Xceed Technologies."** The company is **Exceed Technologies**
(`exceedtech.com`, `jesse.bandre@exceedtech.com`); Creed's own partnership
proposal calls them "Exceed Technology Solutions." The packet README was
internally inconsistent, using both spellings two paragraphs apart.

Corrected here in `generators/field_audit.py`, `pages/26_Field_Audit.py`, and the
packet README. **The three generated files in `docs/audits/tupelo-2026-08/` still
carry the old spelling — rebuild them from the Field Audit page before sending.**

## Finding 4 — Her Gym is filed as a prospect but is already running

`pipeline_opportunities` carries Her Gym as `deal_type='host'`,
`stage='identified'`, created July 14, 2026 — logged as a venue we might sign.
The July 6 sweep shows it already running a live screen with 43 whitelisted
items, eight days before the deal was opened.

Either a screen went in without the CRM catching up, or the deal was opened
against a venue we already host. It is also one of the two venues the packet
flags as having no address anywhere, which fits a record that was never
properly onboarded.

## Finding 5 — Skate Zone's contact email belongs to the Starkville location

Skate Zone in Tupelo (MCTV-101/102) lists `skateodysseystarkville@gmail.com`.
Same manager runs both rinks (Harley Middleton), so this is not wrong exactly,
but venue-level mail for a Tupelo host currently routes through a Starkville
mailbox. Worth confirming a Tupelo-specific address during the audit visit.

---

## Recommended actions

**Before the packet ships to Exceed:**

1. Decide the labeling scheme (Finding 2). Everything else in the packet is
   ready; this is the blocker.
2. Rebuild the three files in `docs/audits/tupelo-2026-08/` so they carry the
   corrected vendor name.
3. Reissue the workbook's Tupelo section at 33 screens, or send a short note
   telling Jesse the August packet supersedes the February roster for Tupelo.
4. Supply addresses for Amsterdam Deli and Her Gym — already flagged in the
   packet as unroutable.

**Commercial, not technical:**

5. Ask Jesse for the audit pricing by territory he offered in February. Six
   months of scope has accumulated without one.
6. Confirm whether the 4–6 month target set in February still stands, or reset it
   now that the Tupelo scope is 57% larger than the roster showed.

**MCTV-side data cleanup:**

7. Create host `clients` records for the six unrostered venues.
8. Resolve Her Gym — convert the pipeline deal or delete it as a duplicate.
9. Harvest contact names from the audit as findings come back; the packet already
   instructs the technician to record who they spoke to.

---

## Contact

**Jesse Bandre'** — Exceed Technologies Tupelo
`jesse.bandre@exceedtech.com` · Mobile 662-871-5515 · Office 662-844-7373

Spelled **Bandre'**, not Bandres. Blake Bandre' (VIBE Aesthetics and Wellness,
MCTV-106) is Jesse's wife, and VIBE Performance and Testosterone is the sister
location — so three of the 27 Tupelo venues, including the one Exceed audits in
its own building, belong to the same family. Worth knowing when scheduling and
when the loop-overrun conversation comes up.
