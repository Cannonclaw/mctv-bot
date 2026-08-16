# Print package — Copy Cow, Starkville

**File to hand over:** `STARKVILLE-Host-Pitch-PRINT.pdf`
**Meeting:** Wednesday 12 August, 10:30 AM · leaving Jackson 8:00 AM

Copy Cow is at 306 University Drive and is **one of our own host venues** — worth
mentioning at the counter, and worth mentioning to Joe.

---

## What to ask for

> "Fifteen pages, letter size, landscape, full colour, printed at actual size.
> Two copies. No binding needed."

That is the whole job. It is a walk-up colour copy run — no bleed, no trim, no
custom stock, nothing that needs a pre-press conversation.

| Spec | Value |
| --- | --- |
| Pages | 15 |
| Size | US Letter, 8.5 × 11 in |
| Orientation | **Landscape** |
| Colour | Full colour |
| Scaling | **Actual size / 100%** — *not* "fit to page" |
| Sides | Single-sided (see below) |
| Paper | Whatever they have in 28–32 lb text. Standard 24 lb is fine. |
| Finishing | None required |
| Copies | 2 — one for Joe, one for you |

**The one thing that can go wrong:** if the operator leaves "fit to page" or
"shrink to fit" on, every slide gets a second white border and the deck looks
timid. The page is already sized with its own margin. Ask for **actual size**.

---

## Choices, in order of how much they matter

**Single-sided vs double-sided.** Single-sided, if the cost is tolerable. It lets
you lay slides side by side on a desk — the board slide next to the economics
slide is a strong physical move, and you cannot do it with a duplexed booklet.
Double-sided is fine if you would rather hand over something slimmer.

**Paper.** Heavier stock reads as more considered, and the cover photograph holds
up better on it. If they offer 32 lb or 100 lb text, take it. If it is a choice
between heavier paper and being late, take standard paper.

**Finishing.** None needed. If you want it to feel finished and they can do it
while you wait: a single staple in the top-left corner, or a clear front cover
with a black comb. Do **not** wait on coil binding.

**Quantity.** Two is right. A third spare is cheap insurance if a page smudges,
and if the marketing staffer sits in you will want one for her.

---

## If something is not available

- **No colour, or the colour printer is down** — do not print in greyscale. The
  cover photograph and the navy/gold system carry the whole thing. Show the deck
  on a laptop instead and post the printed copy afterwards.
- **No landscape** (rare, but some shops default to portrait) — the file itself is
  landscape; they only need to not override it.
- **Running late** — skip the print. The deck is at the artifact link and works on
  any screen, and the lobby board demo is better live than on paper anyway.

---

## Rebuilding the file

```
python scripts/build_starkville_deck.py --pdf --print-package
```

Emits three artefacts from the same source:

| File | For |
| --- | --- |
| `STARKVILLE-Host-Pitch.pdf` | Screen and email — native 1920 × 1080 |
| `STARKVILLE-Host-Pitch-PRINT.pdf` | **This job** — imposed on US Letter landscape |
| `STARKVILLE-Host-Pitch.artifact.html` | The web version behind the artifact link |

The print variant re-anchors `--u` to a hundredth of the target width, so the
whole slide rescales in inches with no transform and no rounding drift. If a
future edit changes the canvas, that one variable is the only thing to touch.

**On a phone, use the PDF, not the artifact link.** The web version scales the
whole 16:9 slide off one CSS variable, which works down to about a laptop but
not to a 390px screen — below roughly 1000px wide, type stops shrinking with the
box and slides 2, 10 and 13 spill past their footers. Nothing is wrong with the
deck; it is a limit of scaling a fixed canvas that far. Laptop, tablet, the PDF
and the printed pages are all unaffected. Fixable with a small-screen breakpoint
if it ever matters.
