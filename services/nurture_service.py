# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Automated nurture sequence service for sales pipeline.

Manages drip campaigns via email and SMS to keep prospects warm.
Tracks sequence progress per opportunity and prevents duplicate sends.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ── Nurture Sequence Definitions ──────────────────────────────────────────────

SEQUENCES = {
    "new_lead": {
        "name": "New Lead Nurture",
        "description": "Warm follow-up sequence for inbound leads",
        "steps": [
            {"step": 1, "delay_days": 1,  "channel": "email", "template": "welcome",
             "description": "Welcome email with MCTV overview"},
            {"step": 2, "delay_days": 3,  "channel": "sms",   "template": "follow_up_3day",
             "description": "Quick SMS check-in"},
            {"step": 3, "delay_days": 7,  "channel": "email", "template": "value_prop",
             "description": "Value proposition deep-dive"},
            {"step": 4, "delay_days": 14, "channel": "email", "template": "social_proof",
             "description": "Social proof and network stats"},
            {"step": 5, "delay_days": 21, "channel": "sms",   "template": "meeting_request",
             "description": "Request a quick call"},
            {"step": 6, "delay_days": 30, "channel": "email", "template": "final_follow_up",
             "description": "Final check-in before cooling off"},
        ],
    },
    "post_proposal": {
        "name": "Post-Proposal Follow-Up",
        "description": "Follow up after sending a proposal",
        "steps": [
            {"step": 1, "delay_days": 1,  "channel": "sms",   "template": "proposal_check_in",
             "description": "Quick check — did you receive it?"},
            {"step": 2, "delay_days": 3,  "channel": "email", "template": "proposal_follow_up",
             "description": "Detailed follow-up with Q&A offer"},
            {"step": 3, "delay_days": 7,  "channel": "sms",   "template": "proposal_reminder",
             "description": "Gentle reminder about the proposal"},
            {"step": 4, "delay_days": 14, "channel": "email", "template": "proposal_final",
             "description": "Final follow-up — limited availability"},
        ],
    },
    "cold_outreach": {
        "name": "Cold Outreach",
        "description": "Outbound prospecting sequence for new targets",
        "steps": [
            {"step": 1, "delay_days": 0,  "channel": "email", "template": "cold_intro",
             "description": "Introduction to MCTV"},
            {"step": 2, "delay_days": 5,  "channel": "sms",   "template": "cold_follow_up",
             "description": "Brief SMS follow-up"},
            {"step": 3, "delay_days": 12, "channel": "email", "template": "cold_value",
             "description": "Why MCTV works for their industry"},
            {"step": 4, "delay_days": 20, "channel": "sms",   "template": "cold_last_chance",
             "description": "Final touchpoint"},
        ],
    },
    "re_engagement": {
        "name": "Re-Engagement",
        "description": "Win back stale or previously lost opportunities",
        "steps": [
            {"step": 1, "delay_days": 0,  "channel": "email", "template": "re_engage_intro",
             "description": "We've been thinking about you"},
            {"step": 2, "delay_days": 7,  "channel": "sms",   "template": "re_engage_offer",
             "description": "Special offer or new feature announcement"},
            {"step": 3, "delay_days": 14, "channel": "email", "template": "re_engage_final",
             "description": "Last attempt with a compelling reason"},
        ],
    },
}


# ── Nurture Email Templates ──────────────────────────────────────────────────

NURTURE_EMAILS = {
    "welcome": {
        "subject": "Welcome to MCTV, {first_name}!",
        "body": """Hi {first_name},

Thanks for your interest in MCTV Elite Advertising! We're excited to show you how indoor digital billboards can help {business_name} reach more local customers.

Quick snapshot of what MCTV offers:
- 125+ screens in restaurants, gyms, salons, and medical offices
- 1.9M+ monthly impressions across Oxford, Starkville, and Tupelo
- Plans starting at just $350/month
- We handle all creative design at no extra cost

One of our team members will be reaching out to learn more about your goals for {business_name}.

In the meantime, feel free to check out our website: www.mctvofms.com

Best,
MCTV Elite Advertising
North Mississippi's Indoor Digital Billboard Network
""",
    },
    "value_prop": {
        "subject": "How {business_name} can reach more customers with MCTV",
        "body": """Hi {first_name},

I wanted to share why local businesses in {city} are choosing MCTV over traditional advertising:

1. CAPTIVE AUDIENCES — Your ad plays where people are waiting, eating, or relaxing. No skipping, blocking, or scrolling past.

2. HYPER-LOCAL TARGETING — Pick the exact venues that match your ideal customer. A gym ad in fitness centers, a restaurant promo at noon in offices.

3. BEST CPM IN THE MARKET — At $1-3 CPM, MCTV delivers more impressions per dollar than radio ($8-12), cable TV ($15-25), or outdoor billboards ($5-8).

4. REAL ANALYTICS — Our NTV360 dashboard shows exactly how many times your ad played, at which venues, and your total reach.

Want to see a custom proposal for {business_name}? Takes 5 minutes — just reply to this email.

Best,
{rep_name}
MCTV Elite Advertising
""",
    },
    "social_proof": {
        "subject": "{first_name}, see what's happening on MCTV screens",
        "body": """Hi {first_name},

Local businesses across North Mississippi are seeing real results with MCTV:

By the numbers:
- 125+ active screens across 3 markets
- 1.9M+ monthly impressions
- 55 minute average viewer dwell time
- Ads play every 15 minutes, 7 days a week

Our advertisers span restaurants, fitness centers, medical offices, salons, real estate, and more. The common thread? They want to stay top-of-mind with local customers in the places they already spend time.

I'd love to put together a quick plan for {business_name}. No commitment — just a look at what's possible.

Reply to this email or give me a call anytime.

Best,
{rep_name}
MCTV Elite Advertising
www.mctvofms.com
""",
    },
    "meeting_request": {
        "subject": "Quick question, {first_name}",
        "body": """Hi {first_name},

I've put together some ideas for how {business_name} could use indoor digital billboards to reach more customers in {city}.

Would you have 10 minutes this week for a quick call? I can walk you through the options and answer any questions.

No pressure at all — just want to make sure you have the info you need to decide if MCTV is a fit.

Best,
{rep_name}
MCTV Elite Advertising
""",
    },
    "final_follow_up": {
        "subject": "Checking in one last time, {first_name}",
        "body": """Hi {first_name},

I wanted to check in one more time about advertising {business_name} on MCTV's indoor digital billboard network.

Quick recap:
- Plans start at $350/month
- No long-term commitment required
- We handle all creative design
- Your ad starts playing within days

If the timing isn't right, no worries. We'll be here when you're ready.

If you'd like to chat, just reply to this email or call us anytime.

Best,
{rep_name}
MCTV Elite Advertising
www.mctvofms.com
""",
    },
    "proposal_follow_up": {
        "subject": "Following up on your MCTV proposal, {first_name}",
        "body": """Hi {first_name},

I wanted to follow up on the advertising proposal I sent for {business_name}.

Did you get a chance to look it over? I'd be happy to:
- Walk through any section in detail
- Adjust the screen count or targeting
- Answer questions about how the billing works
- Show you sample ads from similar businesses

Just reply or give me a call — happy to help however I can.

Best,
{rep_name}
MCTV Elite Advertising
""",
    },
    "proposal_final": {
        "subject": "Your MCTV proposal — limited availability in {city}",
        "body": """Hi {first_name},

Quick heads up — we have limited screen availability in the {city} market, and I wanted to make sure {business_name} has a shot at getting the best placements.

The proposal I sent is still active, and I can lock in your preferred venues if we move forward soon.

No pressure, but I didn't want you to miss out. Let me know if you'd like to chat.

Best,
{rep_name}
MCTV Elite Advertising
""",
    },
    "cold_intro": {
        "subject": "Indoor billboard advertising for {business_name}",
        "body": """Hi {first_name},

I'm {rep_name} from MCTV Elite Advertising. We operate an indoor digital billboard network across {city} — 125+ screens in restaurants, gyms, salons, medical offices, and more.

I think {business_name} would be a great fit for our network. Your ad would play on full HD screens where your ideal customers are already spending time — an average of 55 minutes per visit.

A few things that make MCTV different:
- Ads can't be skipped, blocked, or scrolled past
- Starting at $350/month with no long-term commitment
- We design your ad for free
- Real analytics showing exactly where and how often your ad plays

Would it be worth a quick 10-minute chat to see if this could work for {business_name}?

Best,
{rep_name}
MCTV Elite Advertising
www.mctvofms.com
""",
    },
    "cold_value": {
        "subject": "Why {industry} businesses love MCTV, {first_name}",
        "body": """Hi {first_name},

I reached out last week about MCTV's indoor digital billboard network. I wanted to share why {industry} businesses in particular are a great fit:

Your ideal customers are already in our venues. They're spending 55+ minutes at gyms, restaurants, and salons — and your ad plays automatically throughout their visit.

At $1-3 CPM, you're reaching more people per dollar than any other local advertising option.

I'd love to put together a free custom proposal for {business_name}. No obligation — just a look at the numbers.

Reply to this email or call anytime.

Best,
{rep_name}
MCTV Elite Advertising
""",
    },
    "re_engage_intro": {
        "subject": "We've been thinking about {business_name}, {first_name}",
        "body": """Hi {first_name},

It's been a while since we last connected about MCTV Elite Advertising. A lot has changed since then — we've expanded to 125+ screens and are now delivering 1.9M+ monthly impressions.

I'd love to reconnect and share what's new. If indoor digital billboard advertising is still on your radar, I think you'll be impressed with where we are now.

Want to grab 10 minutes this week?

Best,
{rep_name}
MCTV Elite Advertising
www.mctvofms.com
""",
    },
    "re_engage_offer": {
        "subject": "Special opportunity for {business_name}",
        "body": """Hi {first_name},

We're running a limited promotion for businesses in {city} — and I thought of {business_name}.

For new advertisers, we're offering a free ad design package and a complimentary first month when you sign up for a 12-month plan.

If you've been considering indoor digital billboard advertising, now's a great time to jump in.

Want me to put together a quick proposal? No obligation.

Best,
{rep_name}
MCTV Elite Advertising
""",
    },
    "re_engage_final": {
        "subject": "Last note from MCTV, {first_name}",
        "body": """Hi {first_name},

I don't want to be a pest, so this will be my last note for now.

If indoor digital billboard advertising is ever something {business_name} wants to explore, we're here. Our team would love to help you reach more customers in {city}.

Feel free to reach out anytime — no expiration date on that offer.

Best,
{rep_name}
MCTV Elite Advertising
www.mctvofms.com
""",
    },
}

# ── Nurture SMS Templates ────────────────────────────────────────────────────

NURTURE_SMS = {
    "follow_up_3day": (
        "Hi {first_name}! This is {rep_name} from MCTV. Just checking in on "
        "our conversation about {business_name}. Have any questions? "
        "Feel free to text or call anytime."
    ),
    "proposal_check_in": (
        "Hi {first_name}! Just wanted to make sure you received the MCTV "
        "proposal I sent for {business_name}. Let me know if you have any "
        "questions! —{rep_name}"
    ),
    "proposal_reminder": (
        "Hi {first_name}, quick follow-up on your MCTV proposal for "
        "{business_name}. Happy to walk through it over the phone if "
        "that's easier. —{rep_name}"
    ),
    "cold_follow_up": (
        "Hi {first_name}! {rep_name} from MCTV here. I sent an email about "
        "indoor billboard advertising for {business_name}. Worth a quick chat? "
        "No pressure."
    ),
    "cold_last_chance": (
        "Hi {first_name}, last note from MCTV. If you're ever curious about "
        "indoor digital billboards for {business_name}, just text me back. "
        "—{rep_name}"
    ),
    "meeting_request": (
        "Hi {first_name}! Would you have 10 min this week to chat about MCTV "
        "advertising for {business_name}? I can call anytime that works. "
        "—{rep_name}"
    ),
    "re_engage_offer": (
        "Hi {first_name}! MCTV has a special promotion for businesses in {city}. "
        "Free ad design + first month free with a 12-mo plan. Interested? "
        "—{rep_name}"
    ),
}


# ── Nurture Execution ─────────────────────────────────────────────────────────

def get_sequence_info(sequence_key: str) -> dict | None:
    """Get info about a nurture sequence."""
    return SEQUENCES.get(sequence_key)


def get_available_sequences() -> dict:
    """Return all available nurture sequences."""
    return SEQUENCES


def get_next_step(opp: dict) -> dict | None:
    """Determine the next nurture step for an opportunity.

    Returns the step dict if it's time to send, or None if not ready yet.
    """
    seq_key = opp.get("nurture_sequence")
    if not seq_key or seq_key not in SEQUENCES:
        return None

    current_step = opp.get("nurture_step", 0)
    sequence = SEQUENCES[seq_key]

    # Find the next step
    next_step_num = current_step + 1
    for step in sequence["steps"]:
        if step["step"] == next_step_num:
            # Check if enough time has passed
            last_sent = opp.get("last_nurture_sent")
            if last_sent:
                try:
                    last_dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
                    if isinstance(last_dt, datetime) and last_dt.tzinfo:
                        last_dt = last_dt.replace(tzinfo=None)
                    wait_until = last_dt + timedelta(days=step["delay_days"])
                    if datetime.now() < wait_until:
                        return None  # Not time yet
                except (ValueError, TypeError):
                    pass
            elif current_step > 0:
                # Has previous steps but no timestamp — skip
                return None

            return step

    return None  # Sequence complete


def send_nurture_step(opp: dict, step: dict) -> dict:
    """Execute a nurture step (send email or SMS).

    Args:
        opp: The opportunity dict
        step: The step dict from the sequence

    Returns:
        {"success": bool, "channel": str, "error": str}
    """
    channel = step.get("channel", "email")
    template_key = step.get("template", "")

    # Build template variables
    first_name = (opp.get("contact_name") or "there").split()[0]
    variables = {
        "first_name": first_name,
        "business_name": opp.get("business_name", "your business"),
        "city": opp.get("city", "North Mississippi"),
        "industry": opp.get("industry", "local"),
        "rep_name": opp.get("assigned_rep", "Mary Michael"),
    }

    result = {"success": False, "channel": channel, "error": ""}

    if channel == "email":
        result = _send_nurture_email(opp, template_key, variables)
    elif channel == "sms":
        result = _send_nurture_sms(opp, template_key, variables)

    if result["success"]:
        # Update opportunity with nurture progress
        from services.pipeline_service import update_opportunity, _log_activity
        update_opportunity(opp["id"], {
            "nurture_step": step["step"],
            "last_nurture_sent": datetime.now().isoformat(),
            "last_contact_date": datetime.now().isoformat(),
        })
        _log_activity(
            opp["id"], "nurture_sent",
            details=f"Nurture step {step['step']} ({channel}): {step.get('description', template_key)}"
        )

    return result


def _send_nurture_email(opp: dict, template_key: str, variables: dict) -> dict:
    """Send a nurture email."""
    email = opp.get("contact_email", "")
    if not email:
        return {"success": False, "channel": "email", "error": "No email address"}

    template = NURTURE_EMAILS.get(template_key)
    if not template:
        return {"success": False, "channel": "email", "error": f"Unknown template: {template_key}"}

    try:
        subject = template["subject"].format(**variables)
        body = template["body"].format(**variables)

        from services.notification_service import _send_email
        ok = _send_email(email, subject, body)
        if ok:
            return {"success": True, "channel": "email", "error": ""}
        return {"success": False, "channel": "email", "error": "Email send failed"}
    except Exception as e:
        logger.error("Nurture email failed for %s: %s", opp.get("business_name"), e)
        return {"success": False, "channel": "email", "error": str(e)}


def _send_nurture_sms(opp: dict, template_key: str, variables: dict) -> dict:
    """Send a nurture SMS."""
    phone = opp.get("contact_phone", "")
    if not phone:
        return {"success": False, "channel": "sms", "error": "No phone number"}

    template_text = NURTURE_SMS.get(template_key)
    if not template_text:
        return {"success": False, "channel": "sms", "error": f"Unknown template: {template_key}"}

    try:
        body = template_text.format(**variables)

        from services.sms_service import send_sms
        result = send_sms(phone, body, template=f"nurture_{template_key}")
        if result.get("success"):
            return {"success": True, "channel": "sms", "error": ""}
        return {"success": False, "channel": "sms", "error": result.get("error", "SMS failed")}
    except Exception as e:
        logger.error("Nurture SMS failed for %s: %s", opp.get("business_name"), e)
        return {"success": False, "channel": "sms", "error": str(e)}


def run_nurture_batch() -> list[dict]:
    """Process all opportunities that have pending nurture steps.

    Call this periodically (e.g., daily via briefing or scheduled task).

    Returns:
        List of result dicts: [{business_name, step, channel, success, error}]
    """
    from services.pipeline_service import get_all_opportunities

    results = []
    opps = get_all_opportunities()

    for opp in opps:
        if opp.get("stage") in ("won", "lost"):
            continue
        if not opp.get("nurture_sequence"):
            continue

        step = get_next_step(opp)
        if step is None:
            continue

        result = send_nurture_step(opp, step)
        results.append({
            "business_name": opp.get("business_name", "Unknown"),
            "step": step["step"],
            "channel": result["channel"],
            "success": result["success"],
            "error": result.get("error", ""),
            "description": step.get("description", ""),
        })

    return results


def start_sequence(opp_id: str, sequence_key: str) -> bool:
    """Start a nurture sequence on an opportunity."""
    if sequence_key not in SEQUENCES:
        return False

    from services.pipeline_service import update_opportunity
    update_opportunity(opp_id, {
        "nurture_sequence": sequence_key,
        "nurture_step": 0,
        "last_nurture_sent": None,
    })
    return True


def stop_sequence(opp_id: str) -> bool:
    """Stop the nurture sequence on an opportunity."""
    from services.pipeline_service import update_opportunity
    update_opportunity(opp_id, {
        "nurture_sequence": None,
        "nurture_step": 0,
        "last_nurture_sent": None,
    })
    return True
