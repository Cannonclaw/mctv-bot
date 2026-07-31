# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Mortgage rate fetch cron for the Real Estate Feeds Board rate strip.

Pulls the latest published weekly observation into `market_rates`. Every
board on the network reads that cache, so this runs once and serves all of
them -- no screen ever talks to a rate publisher directly.

Freddie Mac publishes PMMS on Thursdays. Running this daily is deliberate:
a missed Thursday would otherwise leave the strip dark until the following
week, and re-running on an unchanged week is a no-op (market_rates is
unique on series + week_ending).

Exit codes: 0 when every requested series is cached and fresh, 1 otherwise
-- so a cron wrapper can alert on a feed that has gone quiet.

Usage:
    python scripts/fetch_rates.py
    python scripts/fetch_rates.py --series pmms_30yr pmms_15yr
    python scripts/fetch_rates.py --dry-run
"""

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("fetch_rates")

from services import rates_service  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--series", nargs="+", default=["pmms_30yr"],
        choices=sorted(rates_service.SOURCES.keys()),
        help="Rate series to refresh (default: pmms_30yr).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and report without writing to market_rates.",
    )
    args = parser.parse_args()

    failures = []

    for series in args.series:
        if args.dry_run:
            observation = rates_service.fetch_latest(series)
            if observation is None:
                logger.error("%s: no source returned a usable observation", series)
                failures.append(series)
                continue
            logger.info("%s: would store %.2f%% for week ending %s (%s)",
                        series, observation["rate_value"],
                        observation["week_ending"], observation["source_name"])
            # Judge the observation we just pulled, not the database -- a dry
            # run writes nothing, so reading back the cache would report on a
            # state this invocation deliberately did not create.
            week = observation["week_ending"]
        else:
            stored = rates_service.refresh(series)
            if stored is None:
                logger.error("%s: refresh failed", series)
                failures.append(series)
                continue
            logger.info("%s: cached %.2f%% for week ending %s",
                        series, float(stored["rate_value"]), stored["week_ending"])
            week = (rates_service.get_cached_rate(series) or {}).get("week_ending")

        # Fetching successfully is not the same as being displayable. Report
        # the staleness verdict too, because that is what the board acts on.
        if rates_service.is_stale(week):
            logger.warning(
                "%s: newest observation (%s) is older than the %d-day window -- "
                "the rate strip will hide itself on every board",
                series, week, rates_service.staleness_days())
            failures.append(series)

    if failures:
        logger.error("finished with problems: %s", ", ".join(sorted(set(failures))))
        return 1

    logger.info("all series fresh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
