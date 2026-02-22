"""Settings page - configure API key, company info, pricing, and team."""

import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.config_service import load_config, save_config

st.set_page_config(page_title="Settings - MCTV Bot", page_icon="\u2699\uFE0F", layout="wide")

from services.auth import check_password
if not check_password():
    st.stop()

st.markdown("## Settings")
st.caption("Configure your MCTV Elite Advertising Bot.")

config = load_config()

# ── API KEY ───────────────────────────────────────────────────────────────────
st.markdown("### API Configuration")

if os.environ.get("RENDER"):
    st.info("Running on cloud. API key and password are managed in the Render dashboard.")

current_key = os.environ.get("ANTHROPIC_API_KEY", "")
display_key = current_key[:10] + "..." if current_key and current_key != "your-api-key-here" else "Not set"
st.text(f"Current API Key: {display_key}")

new_key = st.text_input("Update API Key", type="password",
                          placeholder="sk-ant-api03-...",
                          help="Your Anthropic API key. This will be saved to the .env file.")

if st.button("Save API Key"):
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

# ── COMPANY INFO ──────────────────────────────────────────────────────────────
st.markdown("### Company Information")

col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("Company Name", value=config["company"]["name"])
    tagline = st.text_input("Tagline", value=config["company"]["tagline"])
with col2:
    website = st.text_input("Website", value=config["company"]["website"])

st.divider()

# ── TEAM MEMBERS ──────────────────────────────────────────────────────────────
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

st.divider()

# ── NETWORK STATS ─────────────────────────────────────────────────────────────
st.markdown("### Network Stats")

nc1, nc2, nc3, nc4 = st.columns(4)
total_screens = nc1.text_input("Total Screens", value=config["network"]["total_screens"])
monthly_impressions = nc2.text_input("Monthly Impressions", value=config["network"]["monthly_impressions"])
avg_dwell = nc3.number_input("Avg Dwell Time (min)", value=config["network"]["avg_dwell_time_minutes"])
plays_per_hour = nc4.number_input("Plays/Hour", value=config["network"]["plays_per_hour"])

st.divider()

# ── MARKETS ───────────────────────────────────────────────────────────────────
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

# ── PRICING ───────────────────────────────────────────────────────────────────
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

st.divider()

# ── SAVE ALL ──────────────────────────────────────────────────────────────────
if st.button("Save All Settings", type="primary", use_container_width=True):
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
