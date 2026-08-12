# Starkville screen audit — packet for Exceed Technologies

Generated 2026-08-12 from the n-compass whitelist sweep dated **2026-07-06**.
Regenerate any time from the bot: **Field Audit** page → Starkville → Build packet.

## What to send

| File | What it is |
|---|---|
| `MCTV_FieldAudit_Starkville.docx` | The brief. Scope, the five things to do at each screen, the capture legend, the route, one reference page per stop with license numbers, and an appendix of known gaps. |
| `MCTV_FieldSheet_Starkville.xlsx` | Where findings get recorded. One row per screen, pre-filled with venue/address/contact/license, with dropdown-validated capture columns. |
| `MCTV_FieldAuditLabels_Starkville.docx` | 34 labels on 4 sheets of **Avery 5163** (4" × 2", ten per sheet). Each carries the venue name, short code, full license number, a QR of that number, and who to call. |

## The numbers

- **34 screens** across **28 venues**, **28 stops**
- **34 of 34** have a license number on file and a printed label
- **4 of 34** run over the 15:00 loop target
- **2 venues** have no address anywhere and are routed by hand at the end

## Read this before quoting the territory

**"Starkville" is not one city.** The Starkville market playlist covers four
screens that are nowhere near Starkville:

| Venue | City | Screens | Rough drive from Starkville |
|---|---|---|---|
| Magnolia Dermatology: Columbus Clinic | Columbus | 1 | ~30 mi |
| Elm Lake Golf Course | Columbus | 2 | ~30 mi |
| Cannon Chevrolet GMC of West Point | West Point | 1 | ~25 mi |

That is 4 of 34 screens sitting in two other towns, and the route puts the
Columbus stops first because they are farthest from the market centre. A
technician handed "Starkville" and expecting a walkable day will find two
out-of-town runs in it.

This is worth settling with Exceed before they price the territory, and it is a
good reason to price Starkville separately from Oxford rather than as one
North Mississippi block.

## Things to know before they go out

1. **Four venues run more than one screen.** Two Brothers Smoked Meats (3), Uno
   Mas Tacos y Tequila Starkville (3), Elm Lake Golf Course (2), Right Track
   Medical Starkville (2). The labels are not interchangeable — each screen has
   its own license.

2. **Two venues share an address** with another MCTV venue: Cellars Wine &
   Spirits and Copy Cow are both at 500 Russell St. One trip covers both.

3. **Two venues have no address anywhere** — not in the host list, the NTV360
   dashboard, or the geocode file. They are listed at the end of the route as
   unroutable, and MCTV needs to supply addresses before the day is scheduled.

4. **Four venues have an address but no geocode**, so they are routed by hand
   rather than slotted into the driving order.

5. **Contact coverage.** 5 venues have no named contact and 7 more have a name
   with no phone. Step 1 — introduce, leave a card, record who you spoke to —
   closes that gap as a side effect of the visit.

6. **One venue disagrees on screen count** between NTV360 and the sweep. Exceed
   should count the physical MCTV screens there.

## When it comes back

Upload the completed spreadsheet on the **Field Audit** page → *Import findings*.
Rows match on license number, so a corrected re-import updates the same screen
instead of duplicating it. Requires migration `scripts/026_screen_assets.sql`
to have been applied in the Supabase SQL editor.
