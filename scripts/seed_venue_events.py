# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Fill the local schedule file with a day of sample Conference Center events.

Dev convenience only. With Supabase configured the service reads the real
`venue_events` table and never touches this file — run migration 025 for the
same sample data on the server side.

    python scripts/seed_venue_events.py            # today, Oxford Conference Center
    python scripts/seed_venue_events.py --clear    # wipe the local file first

Times are relative to today so the board always has something on it.
"""

import argparse
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services import venue_events_service as ves  # noqa: E402

VENUE = "oxford-conference-center"

# (title, host_org, room, start, end, is_private, public_note)
SAMPLE_DAY = [
    ("Lafayette County Chamber Breakfast", "Oxford-Lafayette Chamber of Commerce",
     "Ballroom A", time(7, 30), time(9, 0), False, "Check in at the lobby table"),
    ("North Mississippi Small Business Workshop", "MS Small Business Development",
     "Magnolia Room", time(10, 0), time(12, 30), False, None),
    ("Thompson–Reed Wedding Reception", "Private party",
     "Ballroom B", time(11, 0), time(14, 0), True, None),
    ("Oxford Tourism Council Quarterly", "Visit Oxford",
     "Boardroom", time(13, 30), time(15, 0), False, None),
    ("Ole Miss Alumni Association Reception", "Ole Miss Alumni Association",
     "Ballroom A", time(17, 30), time(20, 0), False, "Doors at 5:15"),
]

SAMPLE_TOMORROW = [
    ("Mississippi Tourism Association Annual Meeting", "MS Tourism Association",
     "Ballroom A + B", time(8, 30), time(16, 0), False, "Registration opens at 8:00"),
]


def seed(clear: bool = False) -> int:
    path = ves._local_path()
    if clear and path.exists():
        path.unlink()
        print(f"cleared {path}")

    tz = ves._tzinfo(ves.venue_config(VENUE)["timezone"])
    today = datetime.now(tz).date()

    created = 0
    for day_offset, rows in ((0, SAMPLE_DAY), (1, SAMPLE_TOMORROW)):
        day = today + timedelta(days=day_offset)
        for title, org, room, start, end, private, note in rows:
            saved = ves.save_event({
                "venue_slug": VENUE,
                "title": title,
                "host_org": org,
                "room": room,
                "starts_at": datetime.combine(day, start, tzinfo=tz),
                "ends_at": datetime.combine(day, end, tzinfo=tz),
                "is_private": private,
                "public_note": note,
                "created_by": "sample",
            })
            if saved:
                created += 1

    print(f"seeded {created} events into {path}")
    return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clear", action="store_true",
                        help="delete the local schedule file before seeding")
    args = parser.parse_args()
    seed(clear=args.clear)
