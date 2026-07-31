# Rafters — Creative Handoff Brief

**Prepared for:** Claude Design
**Prepared by:** MCTV Elite Advertising
**Date:** 2026-07-29
**Status:** Asset handoff — ready to begin content development

---

## 1. The ask

Rafters is an MCTV venue partner in Oxford. The venue sent over a packet of 344 original photos
covering two nights of business. This package compiles that packet, indexes it, and hands it to
design so new content development can start.

---

## 2. Venue profile

| Field | Value |
| --- | --- |
| Name | Rafters Music and Food |
| Address | 1006 E Jackson Ave, Oxford, MS 38655 |
| Category | Live Music Bar (network general category: Family Rec & Entertainment) |
| Contact | Blake Dougherty, General Manager |
| Hours | 10:00 AM – 2:00 AM, seven days a week |
| Relationship | Venue partner / screen host |
| Screens installed | 1 |

### Live network performance

| Metric | Rafters | MCTV network average |
| --- | --- | --- |
| Monthly foot traffic | 4,420 | — |
| **Average dwell time** | **94.6 min** | 55 min |
| Monthly impressions | 27,875 | — |

Source: `data/network_dashboard.json` (NTV360 network dashboard).

**The dwell number is the headline.** At 94.6 minutes, Rafters holds guests roughly 1.7× longer
than the network average. That is the single most important input to the creative direction below.

---

## 3. The photo packet

| | |
| --- | --- |
| Total photos | **344** |
| Total size | **1.81 GB** |
| Format | JPEG, iPhone originals, unedited, no color grading |
| Typical file size | 3.4 – 7.2 MB each |
| Source folder | https://drive.google.com/drive/folders/18YmDNfS5TqEQySsVuCj4BYcpNcClAYtW |
| Folder sharing | Anyone with the link can view |
| Sent by | `231sf4@gmail.com` (shared to Creed's Drive on 2025-07-31) |
| Folder created | 2024-09-30 |

### Shoot sessions

The capture timestamps fall into two clean blocks — two consecutive nights of a single weekend.
All times are US Central Daylight Time.

| Session | Night | Photos | Window |
| --- | --- | --- | --- |
| **A** | Friday night, Sept 27 2024 | 160 | 1:09 AM – 3:14 AM Sat |
| **B** | Saturday night, Sept 28 2024 | 184 | 10:58 PM – 2:13 AM Sun |

Both sessions are late-night, peak-crowd shooting. Session B starts earlier in the evening
(10:58 PM) and therefore likely carries more of the room-filling-up and early-set material;
Session A is entirely post-1:00 AM. Worth confirming against the images before selecting.

This weekend falls on an Ole Miss home football weekend — confirm the specific matchup before
using any game-day framing in copy.

---

## 4. What is in this package

| File | What it is |
| --- | --- |
| `contact-sheet.html` | Browsable visual index of all 344 photos with thumbnails, session filters, and per-photo download links. **Open in a normal browser.** |
| `manifest.csv` | Flat inventory — filename, Drive ID, size, capture time, session, and three URLs per photo. Import into a sheet for selection and status tracking. |
| `manifest.json` | Same data plus venue/source metadata and session rollups, for programmatic use. |
| `HANDOFF-BRIEF.md` | This document. |

### URL patterns (per photo, in both manifests)

- **View in Drive** — `https://drive.google.com/file/d/{DRIVE_ID}/view`
- **Download original** — `https://drive.google.com/uc?export=download&id={DRIVE_ID}`
- **Thumbnail** — `https://drive.google.com/thumbnail?id={DRIVE_ID}&sz=w1200`

To pull the whole set at once, open the source folder, select all, and use Drive's
**Download** action — Drive will zip it server-side.

---

## 5. Creative direction

### The core insight

A 94.6-minute average dwell is unusual. On a screen inside Rafters, a guest will see the same
loop many times over. That reframes the content problem:

- **Rotation matters more than repetition.** A single strong spot repeated for 90 minutes becomes
  wallpaper. Build a deeper rotation and let it breathe.
- **Longer-form works here.** Most MCTV venues need a message that lands in a glance. Rafters can
  carry content that rewards a second and third look — a lineup board, a full week of events,
  a slow-building visual.
- **The screen can earn its place in the room.** In a live-music bar, content that acknowledges
  the night that is actually happening will read as part of the venue rather than an interruption.

### Where the photography fits

These are unedited phone photos of a packed late-night bar. That is a real strength — they look
like the room actually looks — but plan for the constraints:

- **Grade them.** Mixed-source bar lighting, likely warm and noisy. A consistent grade across the
  selected set is the single highest-leverage step before anything gets designed.
- **Crowd energy is the asset.** Wide room shots and crowd-in-motion frames are what a static
  design cannot fake. Prioritize those over detail shots.
- **Faces are cleared.** Usage rights are confirmed, including recognizable patrons — no per-photo
  clearance needed before shipping. Still apply normal judgment: skip frames where someone is
  visibly impaired or otherwise would not want to be the face of the venue.
- **Shoot list the gaps.** Two late-night sessions is one mood. If the content plan needs daytime,
  food, staff, or empty-room hero frames, those will need a second shoot.

### Suggested first pass

1. Cull to a working set of 30–40 across both sessions, weighted toward wide crowd frames.
2. Grade that set to a single consistent look.
3. Build the rotation concepts against the 94.6-minute dwell — plan a set of spots, not one spot.
4. Bring concepts back for internal review before production.

---

## 6. Open items

- [x] **Photo usage rights — cleared.** MCTV has permission to use this packet, including frames
      with recognizable patrons. Confirmed by Creed Cannon, 2026-07-31. Not a blocker for design.
- [ ] Confirm the Ole Miss home matchup for the Sept 27–28 2024 weekend if game-day framing is used.
- [ ] Decide whether a daytime / food / empty-room shoot is needed to round out the library.

### Working assumption on content direction

Rafters is a **screen host / venue partner**, so this package is scoped to **venue-facing content**
— content promoting Rafters that runs on Rafters' own screen. Advertiser-facing work for Rafters
as a paying advertiser would be a separate brief. Flag it if that assumption is wrong; it changes
what gets built.

---

## 7. Provenance note

The photo inventory in this package was built by enumerating the Drive folder directly. Drive's
paginated folder listing returned overlapping pages, so the results were deduplicated by file ID
and then re-verified by re-querying the folder in independent capture-time slices. Two verification
slices returned 36 and 53 files, matching the deduplicated inventory exactly. Gaps in the
`IMG_####` sequence are the sender's own culls, not files missed during collection.

The full-resolution originals were **not** copied into this repository. They live in the source
Drive folder, which is link-shareable; the manifests carry direct download URLs for every file.
This keeps a 1.81 GB binary set out of git while leaving every asset one click away.
