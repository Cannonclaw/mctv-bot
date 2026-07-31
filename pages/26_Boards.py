# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Real Estate Boards — Streamlit page for the MCTV Team Member portal.

Create and manage the dynamic boards sold by the Real Estate Board proposal
(generators/real_estate_board.py), and load the listings that rotate on them.

The board itself lives at /board/<slug> and polls /board/<slug>.json, so a
listing edited here reaches the screen on its next refresh -- no re-render,
no creative request, no trip to the venue.

Drop into: mctv-bot/pages/26_Boards.py
"""
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.board_service import (
    LENDER_MODES,
    add_listing,
    create_board,
    delete_board,
    delete_listing,
    get_listings,
    list_boards,
    render_payload,
    slugify,
    update_board,
    update_listing,
)
from services.config_service import load_config, get_market_names
from services.rates_service import get_cached_rate, is_stale, staleness_days

st.set_page_config(
    page_title="Real Estate Boards - MCTV Bot",
    page_icon="\U0001F3E0",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

config = load_config()

MODE_LABELS = {
    "agent": "Agent",
    "brokerage": "Brokerage",
    "cosponsor": "Agent + Lender co-sponsor",
    "lender": "Lender-branded",
}
THEMES = ["navy", "light", "dark", "sage"]
LISTING_STATUSES = ["active", "pending", "sold", "hidden"]

st.title("\U0001F3E0 Real Estate Boards")
st.caption(
    "Branding holds every frame, listings rotate one at a time, and the rate "
    "strip sits in a fixed corner. Edits here reach the screen on its next "
    "refresh."
)

# ── Rate strip health ────────────────────────────────────────────────────
# Surfaced at the top because a stale feed silently hides the strip on every
# board at once, and that is exactly the kind of thing nobody notices.
cached = get_cached_rate("pmms_30yr")
if not cached:
    st.error(
        "**No mortgage rate cached.** Every rate strip on the network is "
        "hidden until `scripts/fetch_rates.py` runs successfully."
    )
elif is_stale(cached.get("week_ending")):
    st.error(
        f"**Rate feed is stale.** Newest observation is week ending "
        f"{cached.get('week_ending')}, older than the "
        f"{staleness_days()}-day window — the strip is hidden on every board. "
        f"Run `python scripts/fetch_rates.py`."
    )
else:
    st.success(
        f"Rate strip live: **{float(cached['rate_value']):.2f}%** "
        f"(week ending {cached['week_ending']} · {cached.get('source_name', '')})"
    )

# One fetch per rerun, passed into both tabs — same convention as the
# Pipeline and Loop Inventory pages.
boards = list_boards()

tab_manage, tab_new = st.tabs([f"Boards ({len(boards)})", "New board"])


# ── NEW BOARD ────────────────────────────────────────────────────────────
with tab_new:
    st.markdown("### Create a board")

    with st.form("new_board"):
        c1, c2 = st.columns(2)
        with c1:
            display_name = st.text_input("Display Name *", placeholder="Jane Smith")
            brokerage_name = st.text_input("Brokerage", placeholder="Cannon Cleary McGraw")
            phone = st.text_input("Phone")
            email = st.text_input("Email")
            headshot_url = st.text_input("Headshot URL")
        with c2:
            board_mode = st.selectbox(
                "Board Mode", list(MODE_LABELS.keys()),
                format_func=lambda k: MODE_LABELS[k])
            market = st.selectbox("Market", get_market_names(config))
            logo_url = st.text_input("Logo URL")
            theme = st.selectbox("Theme", THEMES)
            rotation_seconds = st.number_input(
                "Seconds per listing", min_value=4, max_value=120, value=12,
                help="How long each listing holds before the next one fades in.")

        slug_input = st.text_input(
            "URL slug", placeholder="jane-smith",
            help="The board plays at /board/<slug>. Leave blank to derive it "
                 "from the display name.")

        show_rate_strip = st.checkbox("Show mortgage rate strip", value=True)

        st.markdown("**Lender** — only rendered for the two lender modes.")
        l1, l2, l3 = st.columns(3)
        lender_name = l1.text_input("Lender Name")
        lender_nmls_id = l2.text_input("Lender NMLS ID")
        lender_logo_url = l3.text_input("Lender Logo URL")

        submitted = st.form_submit_button("Create board", type="primary")

    if submitted:
        if not display_name:
            st.error("Display name is required.")
        elif board_mode in LENDER_MODES and not (lender_name and lender_nmls_id):
            # Enforced here as well as in board_service so the rep finds out
            # now rather than wondering why the lender never showed up.
            st.error(
                "Lender modes need both a lender name and an NMLS ID. The "
                "board suppresses lender branding without the pair — that is "
                "the disclosure rule the proposal commits to."
            )
        else:
            slug = slugify(slug_input or display_name)
            if any((b.get("slug") or "").lower() == slug for b in boards):
                st.error(f"Slug `{slug}` is already taken.")
            else:
                created = create_board({
                    "slug": slug,
                    "board_mode": board_mode,
                    "display_name": display_name,
                    "brokerage_name": brokerage_name,
                    "phone": phone,
                    "email": email,
                    "headshot_url": headshot_url,
                    "logo_url": logo_url,
                    "lender_name": lender_name,
                    "lender_nmls_id": lender_nmls_id,
                    "lender_logo_url": lender_logo_url,
                    "show_rate_strip": show_rate_strip,
                    "rotation_seconds": int(rotation_seconds),
                    "theme": theme,
                    "market": market,
                    "status": "active",
                })
                if created:
                    st.success(f"Created. The board plays at `/board/{slug}`.")
                    st.rerun()
                else:
                    st.error("Could not create the board. Check Supabase config.")


# ── MANAGE BOARDS ────────────────────────────────────────────────────────
with tab_manage:
    if not boards:
        st.info("No boards yet. Create one in the **New board** tab.")
    else:
        for board in boards:
            slug = board.get("slug", "")
            mode = board.get("board_mode", "agent")
            status = board.get("status", "active")
            badge = "" if status == "active" else f" · _{status}_"

            with st.expander(
                f"**{board.get('display_name', '(unnamed)')}** — "
                f"{MODE_LABELS.get(mode, mode)} · /board/{slug}{badge}"
            ):
                listings = get_listings(board["id"])
                visible = [x for x in listings if x.get("status") != "hidden"]

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Listings", len(listings))
                m2.metric("On screen", len(visible))
                m3.metric("Rotation", f"{board.get('rotation_seconds', 12)}s")
                m4.metric("Rate strip", "On" if board.get("show_rate_strip") else "Off")

                st.caption(f"Board URL: `/board/{slug}` · Payload: `/board/{slug}.json`")

                if mode in LENDER_MODES and not (
                    board.get("lender_name") and board.get("lender_nmls_id")
                ):
                    st.warning(
                        "This is a lender-mode board without a complete "
                        "lender name + NMLS ID pair, so lender branding is "
                        "suppressed on screen."
                    )

                # ── Listings ────────────────────────────────────────────
                st.markdown("#### Listings")
                if not listings:
                    st.caption("None yet — the board shows a 'listings coming soon' frame.")

                for listing in listings:
                    lc1, lc2, lc3, lc4 = st.columns([4, 2, 2, 1])
                    lc1.write(f"**{listing.get('address', '')}** · {listing.get('city') or ''}")
                    price = listing.get("price")
                    lc2.write(f"${float(price):,.0f}" if price else "—")
                    new_status = lc3.selectbox(
                        "Status", LISTING_STATUSES,
                        index=LISTING_STATUSES.index(listing.get("status", "active"))
                        if listing.get("status") in LISTING_STATUSES else 0,
                        key=f"ls_{listing['id']}", label_visibility="collapsed")
                    if new_status != listing.get("status"):
                        update_listing(listing["id"], {"status": new_status})
                        st.rerun()
                    if lc4.button("Delete", key=f"ld_{listing['id']}"):
                        delete_listing(listing["id"])
                        st.rerun()

                with st.form(f"add_listing_{board['id']}"):
                    st.markdown("**Add a listing**")
                    a1, a2, a3 = st.columns(3)
                    address = a1.text_input("Address *", key=f"a_{board['id']}")
                    city = a2.text_input("City", key=f"c_{board['id']}")
                    price = a3.number_input("Price", min_value=0.0, step=5000.0,
                                            key=f"p_{board['id']}")
                    b1, b2, b3, b4 = st.columns(4)
                    beds = b1.number_input("Beds", min_value=0.0, step=1.0,
                                           key=f"bd_{board['id']}")
                    baths = b2.number_input("Baths", min_value=0.0, step=0.5,
                                            key=f"ba_{board['id']}")
                    sqft = b3.number_input("Sqft", min_value=0, step=100,
                                           key=f"sf_{board['id']}")
                    photo_url = b4.text_input("Photo URL", key=f"ph_{board['id']}")
                    blurb = st.text_input("Blurb", key=f"bl_{board['id']}")

                    if st.form_submit_button("Add listing"):
                        if not address:
                            st.error("Address is required.")
                        else:
                            add_listing(board["id"], {
                                "address": address,
                                "city": city,
                                "price": price or None,
                                "beds": beds or None,
                                "baths": baths or None,
                                "sqft": int(sqft) or None,
                                "photo_url": photo_url,
                                "blurb": blurb,
                                "status": "active",
                                "sort_order": len(listings),
                            })
                            st.rerun()

                # ── Board controls ──────────────────────────────────────
                st.markdown("#### Board")
                bc1, bc2, bc3 = st.columns(3)
                if bc1.button(
                    "Pause" if status == "active" else "Activate",
                    key=f"toggle_{board['id']}"
                ):
                    update_board(board["id"],
                                 {"status": "paused" if status == "active" else "active"})
                    st.rerun()

                if bc2.button("Preview payload", key=f"prev_{board['id']}"):
                    st.json(render_payload(slug) or {"error": "board not renderable"})

                if bc3.button("Delete board", key=f"del_{board['id']}"):
                    # Listings cascade (migration 025).
                    delete_board(board["id"])
                    st.rerun()
