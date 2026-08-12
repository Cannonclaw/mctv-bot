# Oxford screen audit — packet for Exceed Technologies

Generated 2026-08-12 from the n-compass whitelist sweep dated **2026-07-06**.
Regenerate any time from the bot: **Field Audit** page → Oxford → Build packet.

## What to send

| File | What it is |
|---|---|
| `MCTV_FieldAudit_Oxford.docx` | The brief. Scope, the five things to do at each screen, the capture legend, the route, one reference page per stop with license numbers, and an appendix of known gaps. |
| `MCTV_FieldSheet_Oxford.xlsx` | Where findings get recorded. One row per screen, pre-filled with venue/address/contact/license, with dropdown-validated capture columns. |
| `MCTV_FieldAuditLabels_Oxford.docx` | 48 labels on 5 sheets of **Avery 5163** (4" × 2", ten per sheet). Each carries the venue name, short code, full license number, a QR of that number, and who to call. |

## The numbers

- **48 screens** across **42 venues**, **42 stops**
- **48 of 48** have a license number on file and a printed label — nothing to chase on site
- **1 of 48** runs over the 15:00 loop target (The Velvet Ditch, 15:15)
- Every venue has a street address

Oxford is the cleanest of the three markets and the biggest. It is the one to
run first if Exceed wants a straight production day.

## Things to know before they go out

1. **Five venues run more than one screen.** Right Track Medical (3), and Nail E!,
   Internal Medicine Associates, Amara Salon and Nail Thology (2 each). The
   labels are not interchangeable — each screen has its own license. The brief
   tells the technician to confirm which license is on which player and, if the
   units cannot be told apart, to record both numbers and where each screen
   physically sits.

2. **Six venues share an address with another MCTV venue.** Cannon Chevrolet and
   Cannon Collision are both at 100 N Thacker Lp; Built Different Fitness and
   Nail E! are both at 2580 Jackson Ave W; Magnolia Wine & Spirits and Oxford
   T-Shirt Co. are both at 1453 S Lamar Blvd. One trip covers each pair.

3. **Contact coverage is the weak spot.** 7 venues have no named contact at all
   and 25 more have a name with no phone. Step 1 of the audit — introduce
   yourself, leave a card, write down who you spoke to — is worth as much to us
   here as the hardware check.

4. **Two venues disagree on screen count** between NTV360 and the sweep. Exceed
   should count the physical MCTV screens at those stops; the brief's gaps
   appendix names them.

5. **One venue is not geocoded**, so it is routed by hand at the end rather than
   slotted into the driving order.

## When it comes back

Upload the completed spreadsheet on the **Field Audit** page → *Import findings*.
Rows match on license number, so a corrected re-import updates the same screen
instead of duplicating it. Requires migration `scripts/026_screen_assets.sql`
to have been applied in the Supabase SQL editor.
