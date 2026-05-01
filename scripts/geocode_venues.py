# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""One-shot geocoder for venue addresses.

Reads ``data/network_dashboard.json``, geocodes each address against the
US Census Geocoding API (free, no key, ZCTA-aware), and writes results to
``data/venue_geocodes.json``.

Idempotent: re-run to refresh missing entries; existing matches stay put
unless ``--refresh`` is passed.

Usage:
    python scripts/geocode_venues.py
    python scripts/geocode_venues.py --refresh
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DASHBOARD_PATH = PROJECT_ROOT / "data" / "network_dashboard.json"
GEOCODE_PATH = PROJECT_ROOT / "data" / "venue_geocodes.json"

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"


def geocode(address: str) -> dict | None:
    """Return {lat, lon, matched_address} or None on no match / error."""
    if not address:
        return None
    params = {
        "address": address,
        "benchmark": "Public_AR_Current",
        "format": "json",
    }
    url = f"{CENSUS_URL}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MCTV-Geocoder/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

    matches = (data.get("result") or {}).get("addressMatches") or []
    if not matches:
        return None

    coords = matches[0].get("coordinates") or {}
    return {
        "lat": float(coords.get("y", 0)),
        "lon": float(coords.get("x", 0)),
        "matched_address": matches[0].get("matchedAddress", ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="Re-geocode every venue, ignoring existing entries.")
    ap.add_argument("--limit", type=int, default=0,
                    help="Process at most N venues (for testing).")
    args = ap.parse_args()

    with open(DASHBOARD_PATH, encoding="utf-8") as f:
        venues = json.load(f)["venues"]

    existing = {}
    if GEOCODE_PATH.exists() and not args.refresh:
        with open(GEOCODE_PATH, encoding="utf-8") as f:
            existing = json.load(f)

    out = dict(existing)
    pending = [(k, v) for k, v in venues.items()
               if args.refresh or k not in existing
               or existing[k].get("lat") in (None, 0, 0.0)]
    if args.limit:
        pending = pending[:args.limit]

    print(f"Total venues: {len(venues)}  Already geocoded: {len(existing)}  "
          f"Will process: {len(pending)}")

    success = 0
    fail = 0
    for i, (key, venue) in enumerate(pending, 1):
        addr = venue.get("address", "")
        print(f"[{i}/{len(pending)}] {venue.get('host_name', key)[:40]:40} ", end="")
        sys.stdout.flush()
        result = geocode(addr)
        if result:
            out[key] = result
            print(f"-> ({result['lat']:.4f}, {result['lon']:.4f})")
            success += 1
        else:
            print("-> NO MATCH")
            fail += 1
        # Census API is generous but be polite
        time.sleep(0.3)

    GEOCODE_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nDone. {success} matched, {fail} failed. Saved {len(out)} entries to {GEOCODE_PATH.name}")


if __name__ == "__main__":
    main()
