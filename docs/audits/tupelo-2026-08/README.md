# Tupelo screen audit — packet for Exceed Technologies

Generated 2026-08-04 from the n-compass whitelist sweep dated **2026-07-06**.
Regenerate any time from the bot: **Field Audit** page → Tupelo → Build packet.

## What to send

| File | What it is |
|---|---|
| `MCTV_FieldAudit_Tupelo.docx` | The brief. Scope, instructions, the capture legend, the route, one reference page per stop with license numbers, and an appendix of known gaps. |
| `MCTV_FieldSheet_Tupelo.xlsx` | Where findings get recorded. One row per screen, pre-filled with venue/address/contact/license, with dropdown-validated capture columns. |
| `MCTV_FieldAuditLabels_Tupelo.docx` | 27 labels on 3 sheets of **Avery 5163** (4" × 2", ten per sheet). Each carries the venue name, short code, full license number, a QR of that number, and who to call. |

Tell Exceed to print the label sheet on Avery 5163 stock, run one test page on
plain paper first to check registration, and return the spreadsheet filled in.

## What we're asking for at each screen

Five things, in this order — the brief walks through them:

1. **Introduce yourself and leave a card.** Ask for the manager, explain you look
   after the MCTV screen, and tell them to call you first if it goes wrong.
   Write down who you spoke to; for 12 of these venues we have no contact name.
2. **Confirm it works.** Screen on, loop advancing, and note whether the player
   is on Wi-Fi or a hardline.
3. **Power test it.** Cycle the power and stay until it comes back on its own.
4. **Make it look sharp, then photograph it.** Screen clean, cables concealed,
   nothing in the sightline. Two shots: wide, and close on the Pi.
5. **Label the player and write its license number down.** One label per Pi,
   carrying the venue, the license number, a QR of it, ownership, and who to
   call.

The sheet captures those five things plus the TV's brand, model and size — 16
columns, down from 18, and every one of them earns its place.

## The numbers

- **33 screens** across **27 venues**, **27 stops**
- **27** have a license number on file and a printed label
- **6** do not — all of them at Tupelo Airport Authority
- **22 of 27** measured screens run over the 15:00 loop target

## Things to know before they go out

1. **499 S Gloster St is four licenses in one building.** Midtown Pointe
   Shopping Center *is* 499 S Gloster; Cardiology Associates (Ste B-2), Exceed
   Technologies, and Pizza Doctor are all at that address. One trip covers all
   four. Two more shared addresses: 623 W Main St (Loaded Nutrition + Second
   Skin Waxing) and 1890 McCullough Blvd (Style Society + Premier Aesthetics).

2. **Exceed hosts one of the screens.** Exceed Technologies at 499 S Gloster is
   an MCTV host venue, and its screen runs the longest loop in the market
   (19:59 against a 15:00 target).

3. **The Airport's six license numbers are not in our database.** They exist in
   n-compass under "Tupelo Airport Authority", but the July 2026 sweep only
   covered the oxford/starkville/tupelo playlists, so the airport's special
   playlist was never captured. No labels printed for those six; the brief
   tells the technician to record the numbers on site. To fix it properly, put
   the numbers into `data/audit/extra_licenses.json` and regenerate — labels
   and field-sheet rows appear automatically.

4. **Midtown Pointe screen count disagrees.** NTV360 says two licenses, the
   sweep found one. Exceed should count the physical MCTV screens there.

5. **Right Track Medical's license is cross-market.** License
   `f813363c-6319-40f8-a393-85c49a7f5f53` shows up in the Tupelo sweep *and* on
   one Oxford playlist item. It looks deliberate — flagged so nobody "corrects"
   it in the field.

6. **Two venues have no address anywhere.** Amsterdam Deli and Her Gym are in
   the sweep but absent from the host list, the NTV360 dashboard, and the
   geocode file. They are listed at the end of the route as unroutable. MCTV
   needs to supply addresses. Mudcreek Wine and Spirit has an address but no
   geocode, so it is also routed by hand.

7. **Contact coverage is thin.** 12 venues have no named contact (or only
   "On File"), and 3 more have a name with no phone. The brief tells the
   technician to ask for the manager on duty and record who they spoke to —
   which is worth harvesting back into the host list afterwards.

## When it comes back

Upload the completed spreadsheet on the **Field Audit** page → *Import
findings*. Rows match on license number, so a corrected re-import updates the
same screen instead of duplicating it. Requires migration
`scripts/026_screen_assets.sql` to have been applied in the Supabase SQL editor.
