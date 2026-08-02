# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Create the mTrade Park event feed.

Seeds the feed config researched in docs/MTRADE_PARK_FEED_BRIEF.md, then tries
to resolve their calendar endpoint automatically. Idempotent — running it twice
updates the existing feed rather than creating a second one.

    python scripts/seed_mtrade_feed.py

Discovery needs outbound network access. If it can't reach the site, the feed
is still created and the Source tab's Discover / Import-by-hand both remain
available.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.event_feed_service import (  # noqa: E402
    SOURCE_TYPES,
    discover,
    find_feed_by_slug,
    save_feed,
    update_feed,
)

FEED = {
    "name": "mTrade Park",
    "market": "oxford",
    "venue_name": "mTrade Park",
    "source_url": "https://mtradepark.com",
    "headline": "This Week at mTrade Park",
    "footer": "mtradepark.com",
    # Tournament weekends run Fri-Sun and families book travel well ahead, so a
    # three-week window shows the next few trips rather than just this weekend.
    "window_days": 21,
    "events_per_slide": 4,
    "max_slides": 6,
    # Prospect until they sign — the feed previews and refreshes on demand, but
    # Refresh-all leaves it alone so a venue we don't have yet can't generate
    # noise in the health counts.
    "status": "prospect",
    "notes": (
        "Target: screens in CageTime (7,500 sq ft indoor practice facility, "
        "6 retractable cages, observation deck + concession stand). "
        "2025 USSSA Facility of the Year. Oxford Park Commission facility, "
        "328 Hwy 314. Their site 403s automated fetches from some networks — "
        "if Discover fails, ask for an .ics export or calendar share link."
    ),
}


def main() -> int:
    existing = find_feed_by_slug("mtrade-park")
    if existing:
        feed = update_feed(existing["id"], FEED)
        print(f"Updated existing feed: {feed['name']} ({feed['id']})")
    else:
        feed = save_feed(FEED)
        if not feed:
            print("Could not create the feed.", file=sys.stderr)
            return 1
        print(f"Created feed: {feed['name']} ({feed['id']})")

    print(f"\nProbing {FEED['source_url']} for a calendar endpoint...")
    found = discover(FEED["source_url"])
    if found["source_type"]:
        update_feed(feed["id"], {
            "source_type": found["source_type"],
            "endpoint": found["endpoint"],
        })
        print(f"  Found {SOURCE_TYPES[found['source_type']]}: {found['endpoint']}")
        print(f"  {found['event_count']} events visible.")
        print("\nNext: open Event Feeds -> Slides and hit Refresh now.")
    else:
        print("  No machine-readable calendar reachable. Tried:")
        for attempt in found["attempts"]:
            print(f"    - {attempt['endpoint']}\n        {attempt['detail']}")
        print(
            "\nNext: open Event Feeds -> Source and either re-run Discover from a "
            "network the site accepts, or use Import by hand with an .ics export."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
