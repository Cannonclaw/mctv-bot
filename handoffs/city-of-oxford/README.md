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

## Still to build

A mock of a City message on a real screen — a tornado warning and a "Boil Water Notice —
Ward 3" graphic composited onto a photo of one of our Oxford venues. Concrete beats
abstract in a fifteen-minute meeting, and this is the highest-value remaining prep item.
