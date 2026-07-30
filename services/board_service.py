# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Real Estate Feeds Board data layer.

Backs ``/board/<slug>`` (the page a screen displays) and ``/board/<slug>.json``
(the payload it polls). ``render_payload()`` is the single shape both the
screen and the internal preview consume -- if it isn't in there, the board
can't show it.

Two rules are enforced here rather than in the template, because a template
is the wrong place to keep a promise:

  * The rate strip is omitted entirely when the cached observation is stale.
    ``rate`` is absent from the payload, not blanked, so a template bug can't
    resurrect an old number.
  * Lender identifiers only ride along for the two lender board modes, and the
    name and NMLS ID travel together. Displaying a lender without its NMLS ID
    is the exact mistake the proposal's disclosure section exists to prevent.
"""

from __future__ import annotations

import logging
import re

from services.config_service import load_config
from services.rates_service import rate_for_display
from services.supabase_client import (
    delete_row, insert_row, query_table, update_row,
)

logger = logging.getLogger(__name__)

LENDER_MODES = ("cosponsor", "lender")

# Listings in these states rotate on screen. 'hidden' never renders.
VISIBLE_STATUSES = ("active", "pending", "sold")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """URL segment for a board. Mirrors the rates page's slug convention."""
    return _SLUG_RE.sub("-", (text or "").lower()).strip("-")


# ---------------------------------------------------------------------------
# Boards
# ---------------------------------------------------------------------------

def get_board(slug: str) -> dict | None:
    """Look up a board by slug. Case-insensitive, matching the unique index."""
    if not slug:
        return None
    rows = query_table("boards", filters={"slug": slug.lower()}, limit=1)
    return rows[0] if rows else None


def list_boards(status: str | None = None) -> list[dict]:
    filters = {"status": status} if status else None
    return query_table("boards", filters=filters, order="-created_at")


def create_board(data: dict) -> dict | None:
    payload = dict(data)
    payload["slug"] = slugify(payload.get("slug") or payload.get("display_name", ""))
    return insert_row("boards", payload)


def update_board(board_id: str, data: dict) -> dict | None:
    payload = dict(data)
    if "slug" in payload:
        payload["slug"] = slugify(payload["slug"])
    return update_row("boards", board_id, payload)


def delete_board(board_id: str) -> bool:
    # board_listings cascades on delete (migration 025).
    return delete_row("boards", board_id)


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------

def get_listings(board_id: str, visible_only: bool = False) -> list[dict]:
    rows = query_table("board_listings", filters={"board_id": board_id},
                       order="sort_order")
    if visible_only:
        rows = [r for r in rows if r.get("status") in VISIBLE_STATUSES]
    return rows


def add_listing(board_id: str, data: dict) -> dict | None:
    payload = dict(data)
    payload["board_id"] = board_id
    return insert_row("board_listings", payload)


def update_listing(listing_id: str, data: dict) -> dict | None:
    return update_row("board_listings", listing_id, data)


def delete_listing(listing_id: str) -> bool:
    return delete_row("board_listings", listing_id)


# ---------------------------------------------------------------------------
# Render payload
# ---------------------------------------------------------------------------

def _money(value) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return ""


def _measure(value) -> str:
    """Format a bed/bath count without a pointless trailing zero."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return str(int(number)) if number == int(number) else f"{number:g}"


def _listing_payload(row: dict) -> dict:
    specs = []
    beds = _measure(row.get("beds"))
    baths = _measure(row.get("baths"))
    if beds:
        specs.append(f"{beds} bd")
    if baths:
        specs.append(f"{baths} ba")
    sqft = row.get("sqft")
    if sqft:
        try:
            specs.append(f"{int(sqft):,} sqft")
        except (TypeError, ValueError):
            pass

    status = row.get("status") or "active"
    return {
        "address": row.get("address") or "",
        "city": row.get("city") or "",
        "price": _money(row.get("price")),
        "specs": specs,
        "photo_url": row.get("photo_url") or "",
        "blurb": row.get("blurb") or "",
        # Only non-active states earn a corner flag on the frame.
        "flag": {"pending": "SALE PENDING", "sold": "SOLD"}.get(status, ""),
    }


def render_payload(slug: str, config: dict | None = None) -> dict | None:
    """Everything ``/board/<slug>`` needs to draw itself.

    Returns None when the board doesn't exist or isn't active -- the route
    turns that into a 404 rather than rendering an empty frame.
    """
    board = get_board(slug)
    if not board:
        return None
    if board.get("status") != "active":
        logger.info("board %s requested but status=%s", slug, board.get("status"))
        return None

    cfg = config if config is not None else load_config()
    mode = board.get("board_mode") or "agent"

    listings = [_listing_payload(r)
                for r in get_listings(board["id"], visible_only=True)]

    payload = {
        "slug": board.get("slug"),
        "mode": mode,
        "display_name": board.get("display_name") or "",
        "brokerage_name": board.get("brokerage_name") or "",
        "tagline": board.get("tagline") or "",
        "phone": board.get("phone") or "",
        "email": board.get("email") or "",
        "headshot_url": board.get("headshot_url") or "",
        "logo_url": board.get("logo_url") or "",
        "theme": board.get("theme") or "navy",
        "rotation_seconds": int(board.get("rotation_seconds") or 12),
        "listings": listings,
    }

    # Lender identity rides along only for the lender modes, and only as a
    # pair. A lender name with no NMLS ID doesn't go on screen.
    if mode in LENDER_MODES:
        lender_name = board.get("lender_name") or ""
        nmls = board.get("lender_nmls_id") or ""
        if lender_name and nmls:
            payload["lender"] = {
                "name": lender_name,
                "nmls_id": nmls,
                "logo_url": board.get("lender_logo_url") or "",
                "equal_housing": True,
            }
        elif lender_name:
            logger.warning(
                "board %s is mode=%s with lender_name but no NMLS ID -- "
                "suppressing lender branding", slug, mode)

    # Absent key, not an empty one: a stale rate must be unrenderable.
    if board.get("show_rate_strip"):
        rate = rate_for_display(board.get("rate_series") or "pmms_30yr", config=cfg)
        if rate:
            payload["rate"] = rate

    return payload
