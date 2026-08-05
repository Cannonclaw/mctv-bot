# Van Wallace Insurance Agency (Tupelo, MS) — Design Handoff Package

Concept storyboard for a **:15 silent spot** for Van Wallace Insurance Agency, an advertiser
prospect in the Tupelo market. Built from the brand kit and logo files the client sent on
July 30, 2026.

**4 frames · 1920 × 1080 · 15 seconds · no audio**

## Start here

1. **`HANDOFF-BRIEF.md`** — client profile, brand assets, creative spec, frame-by-frame rationale,
   and the open items that must be closed before production. Read this first.
2. **`spot-storyboard.html`** — the four frames at full size. Open in a browser.
3. **`frames/`** — rendered stills, 1920 × 1080 PNG, for review or pasting into email.

## Before anything ships

Two blockers, both in the brief:

- **"since 1989" is unverified.** It headlines frame 1 and came from a business directory, not
  from Jonathan. Confirm it or cut the date.
- **The logo in frame 4 is a typographic stand-in.** The client's real mark — a wordmark over a
  sage script `Vw` monogram — must be dropped in from the supplied `TRANS *.png` files.

## Source assets

The eleven logo PNGs and the brand kit sheet are attachments on the July 30, 2026 Outlook thread
**"Van Wallace Agency"** (Jonathan Wallace → Creed, Madison Brandon cc'd). They are deliberately
not committed here — pull them from the thread when building production art.

## Regenerating the stills

The PNGs are rendered from `spot-storyboard.html` with headless Chromium at 1920 × 1080. If the
HTML changes, re-render rather than editing the PNGs.

```
chromium --headless --no-sandbox --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1920,1080 \
  --screenshot=frames/frameN.png <single-frame-page>
```

Each frame must be isolated on its own page first — the storyboard's frame labels are display
chrome and sit outside the `.slide` roots so they never export.
