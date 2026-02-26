# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Settings page - configure API key, company info, pricing, and team."""

import streamlit as st
import os
import sys
import secrets
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.config_service import load_config, save_config

st.set_page_config(page_title="Settings - MCTV Bot", page_icon="\u2699\uFE0F", layout="wide")

from services.auth import check_password
if not check_password():
    st.stop()

# ── QuickBooks OAuth Callback Handler ────────────────────────────────────────
# When Intuit redirects back after authorization, the URL will contain
# ?code=xxx&realmId=xxx&state=xxx  — we catch those here BEFORE rendering.
_qb_code = st.query_params.get("code", "")
_qb_realm = st.query_params.get("realmId", "")
_qb_state = st.query_params.get("state", "")

if _qb_code and _qb_realm:
    from services.quickbooks_service import exchange_code
    with st.spinner("Connecting to QuickBooks..."):
        result = exchange_code(_qb_code, _qb_realm)
    if result:
        st.success("QuickBooks connected successfully!")
        st.balloons()
    else:
        st.error("Failed to connect QuickBooks. Please try again.")
    # Clear the URL params so they don't fire again on refresh
    st.query_params.clear()

st.markdown("## Settings")
st.caption("Configure your MCTV Elite Advertising Bot.")

config = load_config()

# ── Tabs ────────────────────────────────────────────────────────────────────

tab_general, tab_network, tab_pricing, tab_integrations, tab_admin = st.tabs([
    "General", "Network", "Pricing", "Integrations", "Admin"
])

# ── TAB: General ────────────────────────────────────────────────────────────

with tab_general:
    # API Configuration
    st.markdown("### API Configuration")

    if os.environ.get("RENDER"):
        st.info("Running on cloud. API key and password are managed in the Render dashboard.")

    current_key = os.environ.get("ANTHROPIC_API_KEY", "")
    display_key = current_key[:10] + "..." if current_key and current_key != "your-api-key-here" else "Not set"
    st.text(f"Current API Key: {display_key}")

    new_key = st.text_input("Update API Key", type="password",
                              placeholder="sk-ant-api03-...",
                              help="Your Anthropic API key. This will be saved to the .env file.")

    if st.button("Save API Key", type="primary"):
        if new_key:
            env_path = Path(__file__).parent.parent / ".env"
            env_path.write_text(f"ANTHROPIC_API_KEY={new_key}\n", encoding="utf-8")
            os.environ["ANTHROPIC_API_KEY"] = new_key
            st.success("API key saved! Reload the page to see the update.")
        else:
            st.warning("Please enter a key.")

    # Model selection
    st.markdown("#### AI Model")
    model_options = {
        "claude-sonnet-4-5-20250929": "Sonnet 4.5 (Fast, cost-effective - recommended for most proposals)",
        "claude-opus-4-6": "Opus 4.6 (Highest quality - for premium proposals)",
    }
    current_model = config["proposal_settings"].get("model", "claude-sonnet-4-5-20250929")
    selected_model = st.selectbox(
        "Claude Model",
        list(model_options.keys()),
        index=list(model_options.keys()).index(current_model) if current_model in model_options else 0,
        format_func=lambda x: model_options[x],
    )

    st.divider()

    # Company Information
    st.markdown("### Company Information")

    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input("Company Name", value=config["company"]["name"])
        tagline = st.text_input("Tagline", value=config["company"]["tagline"])
    with col2:
        website = st.text_input("Website", value=config["company"]["website"])

    st.divider()

    # Team Members
    st.markdown("### Team Members")

    updated_team = []
    for i, member in enumerate(config["team"]):
        with st.expander(f"{member['name']} - {member['title']}", expanded=False):
            tc1, tc2 = st.columns(2)
            name = tc1.text_input("Name", value=member["name"], key=f"team_name_{i}")
            title = tc2.text_input("Title", value=member["title"], key=f"team_title_{i}")
            phone = tc1.text_input("Phone", value=member["phone"], key=f"team_phone_{i}")
            email = tc2.text_input("Email", value=member["email"], key=f"team_email_{i}")
            updated_team.append({"name": name, "title": title, "phone": phone, "email": email})


# ── TAB: Network ────────────────────────────────────────────────────────────

with tab_network:
    st.markdown("### Network Stats")

    nc1, nc2, nc3, nc4 = st.columns(4)
    total_screens = nc1.text_input("Total Screens", value=config["network"]["total_screens"])
    monthly_impressions = nc2.text_input("Monthly Impressions", value=config["network"]["monthly_impressions"])
    avg_dwell = nc3.number_input("Avg Dwell Time (min)", value=config["network"]["avg_dwell_time_minutes"])
    plays_per_hour = nc4.number_input("Plays/Hour", value=config["network"]["plays_per_hour"])

    st.divider()

    # Markets
    st.markdown("### Markets")

    updated_markets = {}
    for market_name, market_data in config["markets"].items():
        with st.expander(f"{market_name} ({market_data['status']})", expanded=False):
            mc1, mc2 = st.columns(2)
            screens = mc1.number_input("Screens", value=market_data["screens"],
                                        key=f"mkt_screens_{market_name}")
            status = mc2.selectbox("Status", ["active", "expanding"],
                                    index=0 if market_data["status"] == "active" else 1,
                                    key=f"mkt_status_{market_name}")
            desc = st.text_area("Description", value=market_data.get("description", ""),
                                 key=f"mkt_desc_{market_name}", height=60)
            updated_markets[market_name] = {"screens": screens, "status": status, "description": desc}

    st.divider()

    # Network Dashboard
    st.markdown("### Network Dashboard")
    st.caption(
        "Upload the MCTV Network Dashboard Excel to store venue metadata "
        "(impressions, dwell time, traffic). This data is used to enrich "
        "traction reports with CPM and impression columns."
    )

    from services.dashboard_service import get_dashboard_status, save_dashboard

    try:
        _db_status = get_dashboard_status()
        if _db_status["loaded"]:
            _updated = _db_status["updated_at"][:10] if _db_status["updated_at"] else "Unknown"
            st.success(
                f"Dashboard loaded: **{_db_status['venue_count']} venues** "
                f"(updated {_updated})"
            )
        else:
            st.warning("No network dashboard stored yet.")
    except Exception:
        st.warning("Unable to check dashboard status.")

    _settings_db_file = st.file_uploader(
        "Upload / Replace Dashboard (.xlsx)",
        type=["xlsx", "xls"],
        key="settings_dashboard_upload",
    )

    if _settings_db_file:
        if st.button("Update Dashboard", type="primary", key="settings_db_update"):
            with st.spinner("Processing dashboard..."):
                try:
                    _result = save_dashboard(_settings_db_file)
                    if _result["success"]:
                        st.success(f"Dashboard saved: {_result['venue_count']} venues")
                        st.rerun()
                    else:
                        st.error(f"Error: {_result.get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error processing dashboard: {e}")


# ── TAB: Pricing ────────────────────────────────────────────────────────────

with tab_pricing:
    st.markdown("### Pricing Tiers")

    updated_tiers = []
    for i, tier in enumerate(config["pricing"]["elite_tiers"]):
        with st.expander(f"{tier['name']} - ${tier['monthly_rate']}/mo", expanded=False):
            pc1, pc2, pc3 = st.columns(3)
            tname = pc1.text_input("Tier Name", value=tier["name"], key=f"tier_name_{i}")
            tscreens = pc2.number_input("Screens", value=tier["screens"], key=f"tier_screens_{i}")
            trate = pc3.number_input("Monthly Rate ($)", value=float(tier["monthly_rate"]),
                                      step=50.0, key=f"tier_rate_{i}")
            tcps = round(trate / tscreens, 2) if tscreens > 0 else 0
            tplays = pc1.text_input("Plays/Month", value=tier.get("plays_per_month", ""),
                                     key=f"tier_plays_{i}")
            updated_tiers.append({
                "name": tname,
                "screens": tscreens,
                "monthly_rate": trate,
                "cost_per_screen": tcps,
                "plays_per_month": tplays,
            })


# ── TAB: Integrations ──────────────────────────────────────────────────────

with tab_integrations:
    st.markdown("### QuickBooks Integration")
    st.caption("Connect QuickBooks Online to sync invoices and track payments automatically.")

    try:
        from services.quickbooks_service import (
            get_connection_status, get_auth_url, disconnect,
            sync_all_clients, sync_unpaid_invoices, get_company_info,
            QB_CLIENT_ID, QB_REDIRECT_URI,
        )

        qb_status = get_connection_status()

        if not qb_status.get("configured"):
            st.warning(
                "QuickBooks API credentials not configured. "
                "Add `QB_CLIENT_ID` and `QB_CLIENT_SECRET` to your .env file."
            )
        elif qb_status.get("connected"):
            # ── Connected state ──────────────────────────────────
            qb_col1, qb_col2 = st.columns([2, 1])
            with qb_col1:
                st.success(f"\u2705 {qb_status.get('message', 'Connected')}")
                st.text(f"Environment: {qb_status.get('environment', 'sandbox').title()}")
                st.text(f"Company: {qb_status.get('company_name', 'Unknown')}")
                st.text(f"Realm ID: {qb_status.get('realm_id', '')}")

            with qb_col2:
                if st.button("\U0001F50C Disconnect QuickBooks", width='stretch'):
                    disconnect()
                    st.info("QuickBooks disconnected.")
                    st.rerun()

            # ── Sync controls ────────────────────────────────────
            st.markdown("#### Sync Operations")
            sync_col1, sync_col2, sync_col3 = st.columns(3)

            with sync_col1:
                if st.button("\U0001F465 Sync All Clients \u2192 QB",
                             width='stretch', key="qb_sync_clients"):
                    with st.spinner("Syncing clients to QuickBooks..."):
                        result = sync_all_clients()
                        st.success(
                            f"Synced {result.get('synced', 0)} clients. "
                            f"Failed: {result.get('failed', 0)}"
                        )

            with sync_col2:
                if st.button("\U0001F4B0 Check QB Payments",
                             width='stretch', key="qb_sync_payments"):
                    with st.spinner("Checking QuickBooks for payments..."):
                        result = sync_unpaid_invoices()
                        st.success(
                            f"Checked {result.get('checked', 0)} invoices. "
                            f"Newly paid: {result.get('newly_paid', 0)}"
                        )

            with sync_col3:
                if st.button("\U0001F4CA Company Info", width='stretch',
                             key="qb_company_info"):
                    info = get_company_info()
                    if info:
                        st.json({
                            "Company": info.get("CompanyName", ""),
                            "Legal Name": info.get("LegalName", ""),
                            "Country": info.get("Country", ""),
                            "Email": info.get("Email", {}).get("Address", ""),
                        })
                    else:
                        st.warning("Could not retrieve company info.")

        else:
            # ── Not connected — show Connect button ─────────────
            st.info(qb_status.get("message", "QuickBooks not connected."))

            # Generate OAuth URL with CSRF state
            if "qb_oauth_state" not in st.session_state:
                st.session_state.qb_oauth_state = secrets.token_hex(16)

            auth_url = get_auth_url(state=st.session_state.qb_oauth_state)

            # Method 1: Copy-paste URL (most reliable — avoids Intuit popup issues)
            st.markdown("**Step 1:** Copy this URL and open it in a new browser tab:")
            st.code(auth_url, language=None)
            st.markdown("**Step 2:** Authorize the app in QuickBooks, then paste the redirect URL below.")
            st.caption("After authorizing, your browser will redirect to a URL starting with "
                       f"`{QB_REDIRECT_URI}?code=...` \u2014 copy the **entire URL** from your browser bar.")

            callback_url = st.text_input(
                "Paste the callback URL here",
                placeholder=f"{QB_REDIRECT_URI}?code=xxx&realmId=xxx&state=xxx",
                key="qb_callback_url",
            )

            if st.button("\u2705 Connect", type="primary", width='stretch', key="qb_connect_btn"):
                if callback_url:
                    try:
                        from urllib.parse import urlparse, parse_qs
                        parsed = urlparse(callback_url)
                        params = parse_qs(parsed.query)
                        code = params.get("code", [""])[0]
                        realm_id = params.get("realmId", [""])[0]
                        if code and realm_id:
                            with st.spinner("Exchanging tokens with QuickBooks..."):
                                result = exchange_code(code, realm_id)
                            if result:
                                st.success("QuickBooks connected successfully!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("Token exchange failed. The authorization code may have expired. Try again.")
                        else:
                            st.error("Could not find `code` and `realmId` in that URL. Make sure you copied the full URL.")
                    except Exception as e:
                        st.error(f"Error parsing URL: {e}")
                else:
                    st.warning("Paste the callback URL from your browser after authorizing.")

            # Method 2: Direct link (may not work with all Intuit apps due to popup behavior)
            with st.expander("Alternative: Direct connect link"):
                st.caption("This opens Intuit's OAuth page directly. If you see an 'undefined' error, use the copy-paste method above instead.")
                st.link_button(
                    "\U0001F517 Connect QuickBooks (Direct)",
                    url=auth_url,
                    width='stretch',
                )

    except ImportError as e:
        st.error(f"QuickBooks service not available: {e}")
    except Exception as e:
        st.error(f"QuickBooks error: {e}")


# ── TAB: Admin ──────────────────────────────────────────────────────────────

with tab_admin:
    # Portal Access Control
    st.markdown("### Portal Access Control")
    st.caption("Only these emails can log into the client portal. Add client emails when ready to open access.")

    from services.auth import _get_allowed_portal_emails

    current_allowed = _get_allowed_portal_emails()
    st.markdown(f"**Currently allowed ({len(current_allowed)}):**")
    for email_addr in sorted(current_allowed):
        st.text(f"  {email_addr}")

    env_val = os.environ.get("PORTAL_ALLOWED_EMAILS", "")
    st.text_input(
        "PORTAL_ALLOWED_EMAILS",
        value=env_val if env_val else "creed@mctvofms.com,mmc@mctvofms.com,swayze@mctvofms.com",
        help="Comma-separated list of emails allowed to access the portal. "
             "Set this in your .env file or Render dashboard to persist changes.",
        disabled=True,
        key="portal_allowed_display",
    )
    st.caption("To add client emails, update PORTAL_ALLOWED_EMAILS in your .env file or Render environment variables.")

    st.divider()

    # Action Items
    st.markdown("### Action Items")
    st.caption("Manual tasks that need human action. Check off items as you complete them.")

    action_items = [
        ("Register copyright at copyright.gov ($65)", "https://eco.copyright.gov/", "Copyright registration required to file lawsuits + unlocks statutory damages up to $150K"),
        ("File trademark for 'MCTV Elite Advertising' ($250-$350)", "https://www.uspto.gov/trademarks/apply", "Search first at tmsearch.uspto.gov, then file in Class 035 (Advertising)"),
        ("1-hour IP attorney consult ($200-$400)", None, "Validate copyright strategy, review ToS, get Mississippi-specific advice"),
        ("Sign up for Twilio SMS", "https://twilio.com/try-twilio", "Get Account SID, Auth Token, and phone number for SMS messaging"),
        ("Register A2P 10DLC in Twilio", None, "Required to send business texts to US numbers at scale (1-2 weeks for approval)"),
        ("Set up bot.mctvofms.com subdomain", None, "CNAME record pointing to Render for custom domain"),
        ("Publish 5 SEO blog posts to WordPress", None, "Drafts ready in seo/blog_drafts/ \u2014 copy-paste into WordPress"),
        ("Fix GBP services list", None, "Still shows Auto Repair/Business Cards \u2014 needs real MCTV services"),
        ("Get first 5 Google reviews", None, "Zero reviews currently \u2014 send review link to existing clients"),
        ("Save 5 community screen photos", None, "Needed in assets/screens/ for proposal auto-include"),
        ("Execute NDAs with any future contractors", None, "Required before sharing codebase access"),
    ]

    for i, (task, link, help_text) in enumerate(action_items):
        col_task, col_link = st.columns([4, 1])
        with col_task:
            st.checkbox(task, key=f"action_{i}", help=help_text)
        with col_link:
            if link:
                st.link_button("Open", link, width='stretch')


# ── Save All Settings ───────────────────────────────────────────────────────

st.divider()
st.caption("Saves changes from General, Network, and Pricing tabs.")

if st.button("Save All Settings", type="primary", width='stretch'):
    config["company"]["name"] = company_name
    config["company"]["tagline"] = tagline
    config["company"]["website"] = website
    config["team"] = updated_team
    config["network"]["total_screens"] = total_screens
    config["network"]["monthly_impressions"] = monthly_impressions
    config["network"]["avg_dwell_time_minutes"] = avg_dwell
    config["network"]["plays_per_hour"] = plays_per_hour
    config["markets"] = updated_markets
    config["pricing"]["elite_tiers"] = updated_tiers
    config["proposal_settings"]["model"] = selected_model

    try:
        save_config(config)
        st.success("All settings saved successfully!")
    except Exception as e:
        st.error(f"Error saving settings: {e}")
