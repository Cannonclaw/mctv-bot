# Grove Collective — :15 Campaign

Three 15-second spots for The Grove Collective, built for MCTV's indoor
network ahead of the 2026 football season.

| # | Spot | Hook | Buy it for |
|---|------|------|-----------|
| 01 | `01-saturdays-arent-free` | "Saturdays aren't free." → **$21 a month** | General market. The workhorse. |
| 02 | `02-ten-thousand-strong` | Counter races 0 → **10,000 members** | The membership drive itself. |
| 03 | `03-ten-dollar-student` | "$10 a month" vs. two coffees | **Oxford only** — student conversion. |
| 04 | `04-first-saturday` | "It's been quiet in Oxford." → **Sept 12** | Awareness. No price, no ask. |
| 90 | `90-first-saturday-social` | Spot 04 re-staged **vertical (1080x1920)** | The collective's own Reels/Stories/TikTok. |

Run 04 first and heavily to warm the market up, then let 01–03 do the
converting. It is the only spot with no price in it, which is what makes it
safe to run before pricing is confirmed.

## Format

Broadcast spots render at **1920x1080, 30fps, 15.000s, H.264** — the spec in
`config/config.json` under `creatomate.resolution` / `duration_seconds`.
Spot 90 declares its own canvas (**1080x1920** vertical) via the `width` /
`height` options on `Spot`; `render.mjs` and `frames.mjs` read the canvas
from the spot, so no flags are needed.

**These are built silent.** MCTV's indoor screens run muted, so nothing in the
creative depends on audio: no voiceover beats, no music-synced cuts, and every
claim is carried by type large enough to read across a dining room. If a spot

ever gets placed somewhere with sound, it needs a re-cut, not just a music bed.

## Rendering

```bash
cd creative/grove_collective
node render.mjs                  # all three spots
node render.mjs 02               # just the membership-drive spot
node render.mjs --fps 30 --crf 16
```

Output lands in `output/videos/grove_collective/` (gitignored — the source of
truth is the HTML, not the MP4).

Requirements: Node 18+, Playwright with Chromium, and an ffmpeg built with
libx264. The ffmpeg that ships with Playwright is VP8-only and will not work;
`pip install imageio-ffmpeg` is the quickest way to get a usable one, and
`render.mjs` finds it automatically.

To check a beat without sitting through a full render:

```bash
node frames.mjs 01 --at 6.4,10.2 --scale 0.5
```

To watch a spot live, serve the folder and open it — it loops, click pauses,
and arrow keys scrub a tenth of a second at a time:

```bash
npx http-server . -p 8080     # then open /spots/01-saturdays-arent-free.html
```

## Dropping in real photography

Every spot is built around named photo slots. With nothing bound they fall
back to a designed field treatment, which is what the current renders show —
**no photography has been placed yet.**

To bind photos, drop the files in `photos/` and declare them before the spot's
module runs:

```html
<script>
  window.PHOTOS = {
    "hero-wide": "../photos/grove-tailgate-wide.jpg",
    "hero-lock": "../photos/grove-crowd-band.jpg",
  };
</script>
```

| Slot | Used in | Size | Wants |
|------|---------|------|-------|
| `hero-wide` | 01 | 1920x1080 | Wide Grove/tailgate atmosphere. Sits behind type — busy centre will fight the headline. |
| `hero-lock` | 01 | 1920x620 | Crowd or Grove tents, horizon low. |
| `crowd-wide` | 02 | 1920x1080 | Packed stands. The busier the better. |
| `lock-band` | 02, 03 | 1920x520 | Members / tailgate scene. |
| `student-wide` | 03 | 1920x1080 | Student section, night game. |
| `grove-wide` | 04 | 1920x1080 | The Grove itself, tents up, people arriving. |

Slots are cropped with `background-size: cover` and a default focal point
around 40% height (faces sit high in most crowd shots). Override per photo
with the third argument to `bindPhoto`, or set `--focal` on the slot.

Each slot already carries a grade toward the campaign palette, so photos from
mixed sources still cut together. Shoot or select wide — every slot animates
with a slow push-in and loses roughly 10% at the edges.

## Before this airs

- [ ] **Brand colors.** `lib/brand.css` uses Ole Miss navy/red/powder blue as a
      stand-in. Swap `--navy`, `--red`, `--powder` for the collective's exact
      hexes.
- [ ] **Confirm the pricing.** The $21/mo entry and $10/mo student tiers come
      from press coverage of the membership drive, not from the collective.
      Tier pricing above those two was inconsistent across sources — confirm
      with the client before anything runs.
- [ ] **Trademark clearance.** These spots reference Ole Miss by name and use
      the university's color identity. That is the client's mark to authorize,
      not ours — get it in writing.
- [ ] **No names, no faces.** Nothing here uses an athlete's or a coach's name,
      image, or likeness, which is deliberate: that is exactly the permission
      an NIL collective cannot casually extend. Any photography added to the
      slots needs the same clearance the client would need for its own channels.
- [ ] **The date in spot 04.** It reads **Sept 12** — Ole Miss's first home
      game of 2026 (Charlotte) and the first Saturday the Grove is open. The
      season opener on Sept 5 or 6 was deliberately not used: it is a
      neutral-site game against Louisville in Nashville, and the exact day was
      still unconfirmed. To change it, edit `GAME_DATE` at the top of
      `spots/04-first-saturday.html` and re-render.
- [ ] **Market plan.** Spot 03 is student-targeted and should not leave Oxford.
      Spots 01 and 04 travel anywhere. Consider holding all four out of the
      Starkville market entirely — see below.

## A note on Starkville

MCTV's network covers Starkville, which is Mississippi State's town. An Ole
Miss NIL membership drive playing on those screens spends impressions on an
audience that will not convert, and risks the host venue asking why it is
running. Recommend Oxford-weighted delivery with Tupelo, Columbus and West
Point as secondary, and Starkville excluded.

## How the spots are built

```
lib/brand.css       design tokens, canvas setup, photo-slot behaviour
lib/spot-engine.js  deterministic timeline — a spot is a function of time
lib/scene.js        procedural stadium: light rig, crowd bowl, atmosphere
spots/*.html        one file per spot, each a beat sheet plus its timeline
render.mjs          frame-exact capture into H.264
frames.mjs          key-frame stills for review
```

Nothing animates on its own. Each spot declares `seek(t)` that paints the
frame for second `t`, and both the browser preview and the renderer drive that
same function. Same input, same pixels, every run — which is why re-rendering
after a copy change is safe, and why a spot can be scrubbed frame by frame
while reviewing.

The stadium is drawn, not filmed: ~1,600 silhouettes in receding rows, one in
eight holding a phone light, lit against a blown-out field horizon. It exists
so these spots read as a packed house without waiting on cleared photography —
and so it can sit behind real photography once that arrives.
