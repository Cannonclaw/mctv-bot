# City of Oxford — Community Partnership Outreach

Materials for approaching the City of Oxford about a standing public-service partnership:
a permanent free slot on all 75 Oxford screens, plus priority handling for urgent City
messages.

**Status:** opening text sent to Mayor Robyn Tannehill on 2026-07-31. Awaiting reply.

## Start here

1. **`OUTREACH-BRIEF.md`** — the strategy. Why now, what the City gets, what we get, the
   guardrails, how the meeting should go, and the follow-up cadence. Read this first.
2. **`follow-up-email.md`** — ready-to-send email if the text goes quiet for ~3 days.
   Copy the body between the rules; the notes underneath are for the sender only.
3. **`build_onepager.py`** — generates the printed leave-behind.
4. **`build_psa_frames.py`** — generates the four sample City messages, plus a
   second printed page showing them. `psa_render.py` holds the shared layout
   primitives.

## Building the one-pager

```
python handoffs/city-of-oxford/build_onepager.py
```

Writes `.docx` and `.pdf` to `output/city/` (gitignored). One page by design — it is a
leave-behind, not a proposal, and it should stay that way.

Reusable for the other markets, which is the point of the flags:

```
python handoffs/city-of-oxford/build_onepager.py --city Starkville --rep "Swayze Hollingsworth"
```

Screen counts, impressions, and the donated value all come from `config/config.json`, so
the numbers stay correct as the network grows. Oxford currently prints as 75 screens,
1.1M+ monthly impressions, and $15,600/year of donated inventory (the 75+ screen tier at
$1,300/month).

### Before printing it

The one-pager promises a turnaround for pushing an urgent message live. It currently
prints the placeholder **"same business day."** Confirm the real number through n-compass
and pass it in:

```
python handoffs/city-of-oxford/build_onepager.py --alert-turnaround "within four hours"
```

Quote it conservatively. A city told "within the hour" that gets four hours during an
actual weather event will not trust the channel again. See section 6 of the brief.

## The sample City messages

```
python handoffs/city-of-oxford/build_psa_frames.py
```

Four 1920×1080 stills — a boil water notice, a tornado warning, a road closure, and an
election reminder — at the network's real spot resolution. Writes to `output/city/psa/`:

- `clean/` — for on-screen demo in the room only; never printed
- `labeled/` — same frames carrying a black **SAMPLE MOCKUP · NOT AN ACTIVE ALERT** bar.
  **Print and circulate only this set.** A risk review concluded the clean frames are
  accurate enough that a photographed clean frame is functionally a counterfeit official
  alert — real issuing offices, real domains, correct safety wording, and the bracketed
  placeholders are the only tell, invisible at phone-photo scale. If the clean look must
  be shown, show it on a screen and collect nothing printed. The tornado frame carries
  the bar even in `clean/`, unconditionally — it names a real federal warning authority
  and is the one frame where brackets alone are an inadequate tell.
- `contact-sheet.png` — all four in one image
- `MCTV_Oxford_Sample_City_Messages.docx/.pdf` — the second printed page for the meeting; embeds the labeled set

**No MCTV logo appears on any frame, deliberately.** A sign operator's mark on an
emergency frame turns a warning into an advertisement, and attribution belongs to the
issuing authority. The MCTV framing lives on the printed page around them instead.

The build enforces its own legibility rules and exits non-zero if a frame breaks one —
headline cap height ≥12% of frame height, ≤5 words, ≤2 lines, headline contrast ≥7:1,
single-line meta, nothing overrunning the footer. Current state: all four pass, headlines
at 13.2–15% cap height, contrast 8.1:1 to 14.4:1.

Design basis, if it's ever questioned: sized for a 43″ panel read at 25 feet by someone
not trying to read it; ANSI Z535 severity logic and its text pairings (orange and yellow
are black-text colors); a monotonic luminance ramp across the four tiers so severity
survives colorblindness and a badly calibrated screen.

### Verification state

The full review pass has now run — all four frames critiqued for legibility and
municipal accuracy, plus a cross-set risk review.

| Item | State |
| --- | --- |
| `oxfordms.net` | **CONFIRMED** as the City of Oxford's official site (the city publishes its real boil-water notices there). `weather.gov` and NWS Memphis as the issuing office for Lafayette County also verified. |
| Road closure and election frames | **Reviewed; fixes applied** (below). |
| Alert turnaround on the one-pager | Still the placeholder. See above. |

Two findings were acted on and are worth knowing about, because they are the kind of
thing a mayor's staff catches:

- **The boil water source line now reads "Oxford Utilities" alone.** It previously also
  credited the state health department. In Mississippi those are two different notice
  types: the utility issues a precautionary notice after a pressure loss or line break,
  and MSDH issues one only after a failed lab sample. The frame depicts the first case,
  so crediting both was a misattribution — and the Utilities director is the person in
  the room most likely to spot it.
- **The tornado affected-area line is bracketed** like the expiry, because NWS warnings
  are polygon-based and routinely cover only part of a county. Hard-coding a county-wide
  string would push "TAKE SHELTER NOW" to screens outside the polygon, which is the
  over-warning failure an emergency manager will raise.
- **The election frame is the municipal version.** It originally paired "City of Oxford"
  with the Secretary of State's precinct locator — a jurisdiction mismatch, since the SoS
  tool covers county-run elections only and Oxford municipal elections are run by the
  Municipal Election Commission, organized by ward. It now reads "[All wards]" and points
  polling-place lookups at the City's own site. A county/state election day version would
  instead credit the Lafayette County Election Commission and point at sos.ms.gov.
- **The road closure frame leads with the location.** The headline was the generic
  instruction ("Use posted detour") while which road was closed sat in the smallest text.
  For a seated viewer the location is the load-bearing fact, so it now takes the
  headline, with the instruction demoted — and bracketed, since short event closures
  have no posted detour. Bonus from review: North Lamar at Molly Barr matches a real
  City of Oxford closure (the roundabout project), so the example reads as researched
  rather than invented.

One critique was deliberately **not** taken: a reviewer wanted the `[bracketed]`
placeholders removed because they read as an unfilled template. They stay. On a mockup
the brackets are the honest signal — they mark every field the City would fill and stop
the frames from asserting specifics nobody has approved. Consistency is the answer to
"looks broken": every genuinely variable field is bracketed, so the frames read as a
template on purpose.
