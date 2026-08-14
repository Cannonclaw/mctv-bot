# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Build the Huntington Bank Arena & Conference Center HOST media kit.

Matches the current MCTV deck language (the "Tupelo Territory Media Kit"
house style): cream + navy spreads, Playfair Display headlines with a red
or gold italic clause, Inter small-caps eyebrows, hairline stat rows,
numbered footers.

    python handoffs/huntington-bank-arena/build_deck.py

Writes deck.html next to this file and renders
output/proposals/MCTV_Host_Media_Kit_Huntington_Bank_Arena.pdf via headless
Chromium. HTML is the source of truth — edit the SLIDES below, rebuild.
"""

import base64
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT_PDF = ROOT / "output" / "proposals" / "MCTV_Host_Media_Kit_Huntington_Bank_Arena.pdf"

# ── Brand tokens (sampled from the current deck) ─────────────────────────────
NAVY = "#111C33"
NAVY_DEEP = "#0C1526"
CREAM = "#F7F4EC"
RED = "#C3312A"
GOLD = "#C2A15C"
INK = "#16223A"


def b64(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


LOGO_WHITE = b64(ROOT / "assets" / "branding" / "mctv_logo_white.png", "image/png")
FONTS = (HERE / "_fonts.css").read_text()

TEAM_DIR = ROOT / "assets" / "team"
HEADSHOTS = {n: b64(TEAM_DIR / f"{n}_headshot.png", "image/png")
             for n in ("mary_michael", "creed", "swayze")}

# Huntington Bank Arena's own green, so the sample spot reads as theirs, not ours.
HBA_GREEN = "#8DC63F"

# ── Photo slots ─────────────────────────────────────────────────────────────
# Drop real photography into handoffs/huntington-bank-arena/photos/ named for a
# slot below and rerun this script — each slot swaps its rendered fallback for
# the photo. Nothing breaks if the folder is empty; that is the shipped state.
#   cover.jpg     full-bleed cover (landscape, 1920x1080 or larger)
#   airport.jpg   a Tupelo Regional screen in place, page 3
#   concourse.jpg the arena concourse or lobby, page 6
PHOTO_DIR = HERE / "photos"


def photo(slot):
    for ext, mime in ((".jpg", "image/jpeg"), (".jpeg", "image/jpeg"), (".png", "image/png")):
        p = PHOTO_DIR / f"{slot}{ext}"
        if p.exists():
            return b64(p, mime)
    return None

# ── Content ─────────────────────────────────────────────────────────────────
VENUE = "Huntington Bank Arena and Conference Center"
CONTACT = "Alli Shackelford"
CONTACT_TITLE = "Director of Marketing"

TUPELO_VENUES = [
    "Tupelo Regional Airport", "Tupelo Airport Authority", "Hotel Tupelo",
    "Tupelo River Coffee", "Midtown Pointe Shopping Center",
    "Cardiology Associates of N. MS", "CrossFit Tupelo", "Her Gym",
    "Loaded Nutrition · Tupelo", "All Shook Up Nutrition", "39759 Nutrition",
    "Premier Aesthetics", "VIBE Aesthetics & Wellness",
    "VIBE Performance & Testosterone", "Right Track Medical Group · Tupelo",
    "Oxford Urology · Tupelo", "Tupelo Small Animal Hospital",
    "Second Skin Waxing", "Sophia Misaki Beauty", "Style Society",
    "Nail E! Tupelo", "Amsterdam Deli", "Pizza Doctor", "662 Wine and Liquor",
    "Mudcreek Wine & Spirit", "Little Magnolia Gifts & Apparel",
    "Aaron Wash Beard Co", "Skate Zone in Tupelo",
]

CPM_ROWS = [  # (label, dollars, width%, highlight)
    ("Magazine", "$65", 100, False),
    ("Television", "$35", 54, False),
    ("Radio", "$27", 42, False),
    ("Social Media", "$19.51", 30, False),
    ("Outdoor Billboards", "$6", 10, False),
    ("MCTV Indoor Network", "$2.63", 5, True),
]

TEAM = [
    ("Mary Michael Cannon", "CEO &amp; Founder", "mmc@mctvofms.com", "662-801-5677", "mary_michael"),
    ("Creed Cannon", "President &amp; Founder", "creed@mctvofms.com", "601-201-8202", "creed"),
    ("Swayze Hollingsworth", "Director of Sales", "swayze@mctvofms.com", "662-907-0404", "swayze"),
    ("Elliot Davis", "MCTV Digital", "elliot@mctvofms.com", "601-896-4922", None),
]


# ── Component helpers ───────────────────────────────────────────────────────
def foot(n=None, note="MCTV DIGITAL, INC &middot; THE INDOOR BILLBOARD COMPANY"):
    """Page number is stamped at assembly, so slides can be reordered freely."""
    return f'<div class="foot"><span>{note}</span><span class="pg">__PG__</span></div>'


def stat(num, label, tone=""):
    return (f'<div class="stat"><div class="stat-num {tone}">{num}</div>'
            f'<div class="stat-label">{label}</div></div>')


def statrow(items, cls=""):
    return f'<div class="statrow {cls}">' + "".join(stat(*i) for i in items) + "</div>"


def numbered(idx, title, body):
    return (f'<div class="num-item"><div class="num-idx">{idx}</div>'
            f'<div><div class="num-title">{title}</div>'
            f'<div class="num-body">{body}</div></div></div>')


def screen(inner, caption, cls=""):
    """A wall-mounted display. Everything inside is a render, never a photo."""
    return (f'<div class="screen {cls}"><div class="bezel"><div class="panel">{inner}</div>'
            f'<div class="gloss"></div></div><div class="mount"></div>'
            f'<div class="screen-cap">{caption}</div></div>')


def sample_spot():
    """A mock Arena spot, drawn in their green so she sees her own creative."""
    return f'''<div class="spot">
      <div class="spot-top"><span class="spot-mark">HUNTINGTON BANK ARENA</span>
        <span class="spot-live">TONIGHT</span></div>
      <div class="spot-mid">
        <div class="spot-kicker">DOORS 6:00 &middot; SHOW 7:00</div>
        <div class="spot-title">Gospel Fest</div>
        <div class="spot-sub">TICKETS AT HBARENA.COM</div>
      </div>
      <div class="spot-rule"></div>
      <div class="spot-foot"><span>SEPT 12 &middot; ARENA BOWL</span><span class="spot-mctv">MCTV</span></div>
    </div>'''


def feed_weather():
    days = [("THU", "94&deg;", "72"), ("FRI", "91&deg;", "70"),
            ("SAT", "88&deg;", "69"), ("SUN", "90&deg;", "71")]
    cols = "".join(f'<div class="wx-d"><div class="wx-dn">{d}</div>'
                   f'<div class="wx-hi">{hi}</div><div class="wx-lo">{lo}&deg;</div></div>'
                   for d, hi, lo in days)
    return f'''<div class="feed wx">
      <div class="feed-top"><span class="feed-lbl">LOCAL WEATHER</span><span>TUPELO, MS</span></div>
      <div class="wx-now"><div class="wx-temp">94&deg;</div>
        <div><div class="wx-cond">Partly Cloudy</div><div class="wx-meta">Feels like 101&deg; &middot; Humidity 64%</div></div></div>
      <div class="wx-week">{cols}</div>
    </div>'''


def feed_news():
    return f'''<div class="feed news">
      <div class="feed-top"><span class="feed-lbl">LOCAL &amp; WORLD NEWS</span><span>UPDATED 2:40 PM</span></div>
      <div class="nw-lead">Lee County breaks ground on new industrial park</div>
      <div class="nw-rows">
        <div class="nw-r"><span>MS</span>Highway 45 resurfacing begins Monday</div>
        <div class="nw-r"><span>SPORTS</span>Rebels open camp with 14 returning starters</div>
        <div class="nw-r"><span>NAT</span>Markets close higher for a third session</div>
      </div>
    </div>'''


def feed_trivia():
    return f'''<div class="feed triv">
      <div class="feed-top"><span class="feed-lbl">FUN FACT</span><span>DID YOU KNOW?</span></div>
      <div class="tv-q">Tupelo built the first city-owned<br>power system in the nation<br>to buy TVA electricity.</div>
      <div class="tv-a">1934 &middot; Tupelo, Mississippi</div>
    </div>'''


def event_board():
    """A faithful miniature of static/board.html — the real product, not a concept."""
    rows = [
        ("5:30 PM", "Chamber of Commerce Reception", "Tupelo CDF", "PRE-FUNCTION", ""),
        ("6:00 PM", "Doors Open", "Gospel Fest", "ARENA BOWL", "soon"),
        ("7:00 PM", "Gospel Fest", "Live Nation", "ARENA BOWL", ""),
        ("7:00 PM", "Private Event", "", "MEETING RM 3", "private"),
    ]
    tr = "".join(
        f'<div class="brow {c}"><div class="btime">{t}</div>'
        f'<div class="btitle"><div class="bn">{n}</div>'
        f'{f"<div class=bo>{o}</div>" if o else ""}</div>'
        f'<div class="broom">{r}</div></div>'
        for t, n, o, r, c in rows)
    return f'''<div class="board">
      <div class="bhead">
        <div><div class="bvenue">Huntington Bank Arena</div>
          <div class="btag">TODAY AT THE ARENA</div></div>
        <div class="bclock"><div class="btime-now">2:41<span>PM</span></div>
          <div class="bdate">Thursday, August 13</div></div>
      </div>
      <div class="bnowlbl"><span class="bdot"></span>HAPPENING NOW</div>
      <div class="bnow">
        <div class="bnow-when">1:00 – 4:30<div class="bnow-r">BALLROOM A</div></div>
        <div class="bnow-what"><div class="bnow-n">Lee County Schools In-Service</div>
          <div class="bnow-o">Lee County School District</div></div>
      </div>
      <div class="bnextlbl">COMING UP<span class="bpage">1 / 1</span></div>
      {tr}
      <div class="bbrand"><b>MCTV<span>&middot;</span></b><span>HUNTINGTON BANK ARENA</span></div>
    </div>'''


# ── Slides ──────────────────────────────────────────────────────────────────
def slide_01_cover():
    hero = photo("cover")
    art = (f'<div class="cover-photo" style="background-image:url({hero})"></div>'
           '<div class="cover-scrim"></div>') if hero else \
        '<div class="cover-glow"></div><div class="cover-rules"></div>'
    return f'''
<section class="slide navy cover">
  {art}
  <img class="cover-logo" src="{LOGO_WHITE}" alt="MCTV Elite Advertising">
  <div class="cover-tag">HUNTINGTON BANK ARENA &amp; CONFERENCE CENTER &middot; TUPELO</div>
  <div class="cover-body">
    <h1 class="display cover-h1">Upgrade the arena.<br><em>We'll cover it.</em></h1>
    <div class="cover-sub">THE INDOOR BILLBOARD COMPANY &middot; NORTH MISSISSIPPI</div>
  </div>
  <div class="cobrand"><span class="cobrand-bar"></span>
    <span class="cobrand-t">A VENUE PARTNERSHIP PROPOSED FOR HUNTINGTON BANK ARENA</span></div>
  <div class="prepared">
    <div class="prepared-label">PREPARED FOR</div>
    <div class="prepared-name">{CONTACT}</div>
    <div class="prepared-org">{CONTACT_TITLE} &middot; {VENUE}</div>
  </div>
  <div class="foot cover-foot"><span>HOST MEDIA KIT &middot; TUPELO &middot; AUGUST 2026</span>
    <span>WWW.MCTVOFMS.COM</span></div>
</section>'''


def slide_02_proposal():
    return f'''
<section class="slide cream">
  <div class="eyebrow">THE PARTNERSHIP</div>
  <h2 class="display">What we're <em>proposing</em>.</h2>
  <div class="two-col">
    <div class="col-left">
      <p class="body">You told us you're looking for ways to modernize the facility. This is
      one that costs the arena nothing and pays it every month.</p>
      <p class="body">We install and own the screens. We sell, produce and service the
      advertising on them. You provide the wall space and the power &mdash; and take a share
      of everything that runs.</p>
      <p class="body accent">It's the same structure Tupelo Regional Airport's board
      approved in March. Those screens went live in April.</p>
      {screen(sample_spot(), "SAMPLE ARENA SPOT &middot; BUILT BY US, APPROVED BY YOU", "sm")}
    </div>
    <div class="col-right">
      {numbered("01", "We install the screens", "Commercial-grade displays through the concourse, lobby and conference space. Hardware, mounts, media players, install labor, maintenance and replacement are all ours. No capital request, no line item in your budget.")}
      {numbered("02", "You earn on every ad", "A 60/40 split on every advertiser that runs on your screens &mdash; and the 60 follows whoever brought them in. We source it, you take 40%. You source it, you take 60%. Paid monthly, with a proof-of-play and billing report behind it.")}
      {numbered("03", "Your events run network-wide", "Your calendar promoted across all 125+ MCTV screens in Tupelo, Oxford and the Golden Triangle. At no charge, for as long as we're partners.")}
    </div>
  </div>
  {statrow([("$0", "COST TO THE ARENA"), ("60/40", "WHOEVER BRINGS THE ADVERTISER", "red"),
            ("125+", "SCREENS PROMOTING YOU"), ("24/7", "SCREENS ON")])}
  {foot(2)}
</section>'''


def slide_03_airport():
    return f'''
<section class="slide navy">
  <div class="eyebrow gold">PROOF &middot; SAME MARKET, SAME STRUCTURE</div>
  <h2 class="display">We just did this at <em>Tupelo Regional</em>.</h2>
  <div class="two-col">
    <div class="col-left">
      <p class="body">In March, the Tupelo Airport Authority board reviewed and approved our
      Venue Partner Agreement &mdash; the same 60/40 origination split, content-approval process and
      grandfathering language we're offering you. Legal had no changes.</p>
      <p class="body">Exceed Technologies handled the install. Five screens now run across the
      lobby, center lobby, ticket counter, baggage claim and the sterile corridor. They came
      online cleanly, sit on the terminal's UPS and generator backing, and run 24/7.</p>
      <p class="body">MCTV carries general liability with the Authority named as an additional
      insured, primary and non-contributory, with notice of cancellation. We'd do the same for
      the Arena.</p>
    </div>
    <div class="col-right">
      <div class="quote-card">
        <div class="quote-mark">&ldquo;</div>
        <p class="quote">The overall setup looks great and makes a noticeable difference in the
        terminal. It gives the space a more modern and updated feel and ties everything together
        well across the different areas.</p>
        <div class="quote-attr">IT DIRECTOR &amp; MARKETING COORDINATOR<br>
        <span>TUPELO REGIONAL AIRPORT &middot; APRIL 2026</span></div>
      </div>
    </div>
  </div>
  {statrow([("5", "TERMINAL SCREENS", "gold"), ("~30", "DAYS TO LIVE"),
            ("$0", "AIRPORT CAPITAL"), ("0", "CHANGES FROM LEGAL")], "bordered")}
  {foot(3)}
</section>'''


def slide_04_network():
    bars = "".join(
        f'<div class="bar-row{" hi" if hi else ""}"><div class="bar-label">{label}</div>'
        f'<div class="bar-track"><div class="bar" style="width:{w}%"><span>{amt}</span></div></div></div>'
        for label, amt, w, hi in CPM_ROWS)
    return f'''
<section class="slide cream">
  <div class="eyebrow">ELITE ADVERTISING</div>
  <h2 class="display">The network &amp; the value.</h2>
  {statrow([("125+", "DIGITAL SCREENS"), ("28", "TUPELO / LEE CO.", "red"),
            ("1.9M+", "IMPRESSIONS / MO"), ("55+", "MIN AVG DWELL"), ("3", "GROWTH MARKETS")], "top")}
  <div class="cpm-head">
    <h3 class="display sm">Local CPM comparison.</h3>
    <p class="micro">CPM = cost per thousand impressions. The MCTV figure is the network blended
    average; campaigns price as low as $1.64 CPM at scale. Comparison figures are typical U.S.
    local CPM ranges by channel.</p>
  </div>
  <div class="bars">{bars}</div>
  {foot(4)}
</section>'''


def slide_05_footprint():
    half = (len(TUPELO_VENUES) + 1) // 2
    cols = "".join(
        '<ul class="venue-col">' + "".join(f"<li>{v}</li>" for v in col) + "</ul>"
        for col in (TUPELO_VENUES[:half], TUPELO_VENUES[half:]))
    return f'''
<section class="slide cream">
  <div class="eyebrow">HOST NETWORK &middot; TUPELO / LEE COUNTY</div>
  <h2 class="display">The company you'd <em>keep</em>.</h2>
  <p class="body wide">28 premier Tupelo &amp; Lee County venues already host MCTV screens
  &mdash; and 125+ across the full North Mississippi network. Your advertisers are already
  seeing these rooms.</p>
  <div class="chip-row">
    <div class="chip filled"><div class="chip-num">28</div><div class="chip-label">TUPELO / LEE CO.</div></div>
    <div class="chip"><div class="chip-num">44</div><div class="chip-label">OXFORD / LAFAYETTE</div></div>
    <div class="chip"><div class="chip-num">29</div><div class="chip-label">GOLDEN TRIANGLE</div></div>
  </div>
  <div class="venue-cols">{cols}</div>
  {foot(5)}
</section>'''


def slide_06_placement():
    zones = [
        ("Main concourse &amp; concessions", "Where a full house queues and stands. The highest-dwell wall in the building on an event night."),
        ("West entry &amp; box office lobby", "First surface every guest passes. Wayfinding, tonight's event, upcoming on-sales."),
        ("The link corridor &amp; flex space", "The connector everyone walks between the arena and the conference center. Captive, and it works on both event nights and meeting days."),
        ("Exhibit hall &amp; pre-function", "Trade shows, conventions and receptions. Booth wayfinding, sponsor recognition, today's schedule."),
        ("Meeting room corridor", "Room assignments and today's agenda, rendered live off your calendar."),
        ("Club / VIP level", "Glass-walled and visible off the concourse. Premium inventory for premium advertisers, priced accordingly."),
    ]
    items = "".join(
        f'<div class="zone"><div class="zone-i">{i:02d}</div>'
        f'<div><div class="zone-t">{t}</div><div class="zone-b">{b}</div></div></div>'
        for i, (t, b) in enumerate(zones, 1))
    return f'''
<section class="slide navy">
  <div class="eyebrow gold">PROPOSED PLACEMENT</div>
  <h2 class="display">Where your screens <em>would go</em>.</h2>
  <p class="body wide dim">A starting map, not a final one &mdash; drawn from the outside, before
  we've walked it with you. Your building does two different jobs, event nights and meeting days,
  and the screens should earn on both. We'd set the exact count and positions together, then work
  the install around your calendar so nothing lands on a show day.</p>
  <div class="zones">{items}</div>
  {statrow([("6&ndash;8", "PROPOSED SCREENS", "gold"), ("6", "ZONES"),
            ("$0", "CAPITAL COST"), ("You", "APPROVE EVERY SPOT")], "bordered")}
  {foot(6)}
</section>'''


def slide_07_package():
    cards = [
        ("INSTALLED &amp; MAINTAINED", "$0",
         ["Commercial-grade displays", "Mounts, media players, cabling", "Install labor &amp; project management",
          "Maintenance, service &amp; replacement"]),
        ("CONTENT, MANAGED", "$0",
         ["Local weather, news &amp; sports", "Trivia, fun facts, live feeds", "Balanced against advertising",
          "Managed daily by our team"]),
        ("YOUR OWN AIRTIME", "$0",
         ["Dedicated Arena spots in your loop", "Events, concessions, sponsors", "Wayfinding &amp; house messaging",
          "Unlimited changes, built in-house"]),
        ("NETWORK AIRTIME", "$0",
         ["Your calendar on 125+ screens", "Tupelo, Oxford &amp; Golden Triangle",
          "Promote every event you host", "Refreshed as your calendar moves"]),
    ]
    html = "".join(
        f'<div class="pkg"><div class="pkg-h">{h}</div><div class="pkg-p">{p}<span>/mo</span></div>'
        + "".join(f'<div class="pkg-li">{li}</div>' for li in lis) + "</div>"
        for h, p, lis in cards)
    return f'''
<section class="slide navy">
  <div class="eyebrow gold">YOUR HOST PACKAGE</div>
  <h2 class="display">What it costs you: <em>nothing</em>.</h2>
  <div class="pkgs">{html}</div>
  <div class="pkg-foot">
    <span class="star">&#9733;</span><span class="pkg-foot-t">Total cost to the Arena &mdash;
    $0, for the life of the agreement.</span>
    <span class="pkg-foot-b">You provide wall space and power. We provide everything else
    &mdash; and pay you up to 60% of what the screens earn.</span>
  </div>
  {foot(7)}
</section>'''


def slide_07_feed():
    """What actually runs in the loop — content sold the airport, and it sells venues."""
    cells = [
        (feed_weather(), "LOCAL WEATHER"),
        (feed_news(), "LOCAL &amp; WORLD NEWS"),
        (feed_trivia(), "TRIVIA &amp; FUN FACTS"),
        (sample_spot(), "YOUR EVENT SPOT"),
    ]
    grid = "".join(
        f'<div class="fcell">{screen(inner, cap, "xs")}</div>' for inner, cap in cells)
    return f'''
<section class="slide navy">
  <div class="eyebrow gold">WHAT'S ON THE SCREEN</div>
  <h2 class="display">Not a wall of <em>ads</em>.</h2>
  <p class="body wide dim">A 15-minute loop, refreshed continuously. Advertising is interleaved
  with content people actually want &mdash; which is why they keep looking up, and why the
  advertising works. Your Arena spots sit inside the same rotation.</p>
  <div class="fgrid">{grid}</div>
  {statrow([("15", "MINUTE LOOP", "gold"), ("4&times;", "PLAYS PER HOUR"),
            ("1,500+", "PLAYS PER SCREEN / MO"), ("55+", "MIN AVG DWELL")], "bordered")}
  {foot()}
</section>'''


def slide_13_team():
    """Real headshots. The people who sign the agreement answer the phone."""
    cards = "".join(
        f'<div class="tcard"><div class="tface" style="background-image:url({HEADSHOTS[k]})"></div>'
        f'<div class="tname">{n}</div><div class="trole">{r}</div>'
        f'<div class="tcontact">{e}<br>{p}</div></div>'
        for n, r, e, p, k in TEAM if k)
    return f'''
<section class="slide cream">
  <div class="eyebrow">WHO YOU'D BE WORKING WITH</div>
  <h2 class="display">Owner-operated, <em>and local</em>.</h2>
  <p class="body wide">We are not a franchise and not a rep firm. The people who sign your
  agreement are the same people who answer the phone when a screen needs attention, and the
  same people who will walk your building with you.</p>
  <div class="tcards">{cards}</div>
  {statrow([("125+", "SCREENS WE OWN AND RUN", "red"), ("28", "TUPELO / LEE CO. VENUES"),
            ("100%", "CREATIVE BUILT IN-HOUSE"), ("24/7", "SUPPORT, FROM US")], "bordered")}
  {foot()}
</section>'''


def slide_08_revshare():
    rows = [("4 advertisers we bring", "$1,400", "40%", "$560"),
            ("4 advertisers you bring", "$1,400", "60%", "$840"),
            ("Combined", "$2,800", "&mdash;", "$1,400")]
    trs = "".join(
        f'<tr{" class=tot" if a == "Combined" else ""}><td>{a}</td><td>{b}</td>'
        f'<td>{c}</td><td class="hi">{d}</td></tr>'
        for a, b, c, d in rows)
    return f'''
<section class="slide cream">
  <div class="eyebrow">THE ECONOMICS</div>
  <h2 class="display">Sixty / forty. <em>Whoever brings the advertiser.</em></h2>
  <div class="two-col">
    <div class="col-left">
      <p class="body">Every advertiser on your screens pays a monthly rate, and that rate splits
      <strong>60/40 in favor of whoever brought them in.</strong></p>
      <p class="body">We go find an advertiser, you take 40% of them for doing nothing. You bring
      one &mdash; a sponsor, a vendor, someone already renting your building &mdash; and
      <strong>you take 60%.</strong> Your existing sponsor relationships are suddenly worth
      more than they were.</p>
      <p class="body">We still produce, bill and service every spot either way. Paid monthly with
      a report of what ran and what it billed. No minimums, no clawbacks &mdash; an empty screen
      costs you nothing.</p>
      <p class="body accent">Existing advertiser relationships are grandfathered on both sides.
      Anything the Arena has already sold stays 100% yours.</p>
    </div>
    <div class="col-right">
      <table class="econ">
        <thead><tr><th>Who brings them</th><th>Ad revenue / mo</th>
          <th>Arena share</th><th>Arena / mo</th></tr></thead>
        <tbody>{trs}</tbody>
      </table>
      <p class="micro">Illustrative only, at a $350/mo blended advertiser rate &mdash; not a
      guarantee of earnings. The combined case above runs to $16,800 a year to the Arena. Actual
      revenue share depends on how many advertisers run and who sources them. We'd model this
      properly against your traffic once we've walked the building.</p>
    </div>
  </div>
  {statrow([("60%", "ON EVERY ADVERTISER YOU BRING", "red"), ("40%", "ON EVERY ONE WE BRING"),
            ("$0", "IF A SCREEN SITS EMPTY"), ("100%", "OF YOUR EXISTING DEALS, KEPT")], "bordered")}
  {foot(8)}
</section>'''


def slide_09_events():
    return f'''
<section class="slide navy">
  <div class="eyebrow gold">THE OTHER HALF OF THE DEAL</div>
  <h2 class="display">Your calendar, on <em>every screen we own</em>.</h2>
  <div class="two-col">
    <div class="col-left">
      <p class="body">The screens in your building are only half of it. The bigger asset is the
      other 125+ &mdash; every clinic waiting room, gym, salon and restaurant in Tupelo, Oxford
      and the Golden Triangle where we already run.</p>
      <p class="body">We put your event calendar on all of them. Every show, every on-sale, every
      conference booking window, in front of roughly 1.9 million monthly impressions of the exact
      people you're trying to get through the doors.</p>
      <p class="body">You're currently buying that reach. As a host, you'd have it.</p>
      <p class="body accent">And in your own lobby: an airport-style board showing what's on
      now, what's next, and which room &mdash; live off your calendar, Central time, with
      private bookings masked automatically. Built for the Oxford Conference Center. Yours
      at no cost.</p>
    </div>
    <div class="col-right">
      {screen(event_board(), "YOUR LOBBY EVENT BOARD &middot; LIVE OFF YOUR CALENDAR")}
    </div>
  </div>
  {statrow([("125+", "SCREENS CARRYING YOUR EVENTS", "gold"), ("1.9M+", "IMPRESSIONS / MO"),
            ("4&times;", "PLAYS PER HOUR"), ("15", "MINUTE LOOP")], "bordered")}
  {foot(9)}
</section>'''


def slide_10_whoweare():
    return f'''
<section class="slide navy">
  <div class="eyebrow gold">WHO WE ARE</div>
  <div class="two-col wide-gap">
    <div class="col-left">
      <h2 class="display big">The fastest-growing<br>owner-operated indoor<br>billboard network in<br><em>North America.</em></h2>
    </div>
    <div class="col-right pad-top">
      <p class="body">Our mission is to help local businesses reach their audience. Every month,
      thousands of North Mississippians see our screens &mdash; and remember them.</p>
      <p class="body">We are owner-operated and local. The people who sign your agreement are the
      people who answer the phone when a screen needs attention.</p>
      <p class="body">Join the businesses prioritizing hyper-local advertising that can't be
      skipped, blocked, or scrolled past.</p>
    </div>
  </div>
  {statrow([("125+", "DIGITAL SCREENS"), ("28", "TUPELO / LEE CO. VENUES", "gold"),
            ("1.9M+", "IMPRESSIONS / MO"), ("3", "GROWTH MARKETS")], "bordered")}
  {foot(10)}
</section>'''


def slide_11_next():
    steps = [
        ("Walkthrough &amp; screen survey", "We walk the arena and conference center with you, agree the placements and the count. About an hour of your time."),
        ("Venue Partner Agreement &amp; COI", "The same document the Airport Authority's board approved. The Arena is named as an additional insured on our general liability policy."),
        ("Equipment &amp; install", "Ordered on execution. Installed by Exceed Technologies, scheduled around your event calendar."),
        ("Content build", "We build your Arena spots and the lobby event board. Nothing goes on screen without your approval."),
        ("Live &mdash; and earning", "Screens run 24/7. Your first revenue-share report follows the first month of billing."),
    ]
    items = "".join(
        f'<div class="step"><div class="step-i">{i:02d}</div><div class="step-line"></div>'
        f'<div class="step-t">{t}</div><div class="step-b">{b}</div></div>'
        for i, (t, b) in enumerate(steps, 1))
    return f'''
<section class="slide cream">
  <div class="eyebrow">NEXT STEPS</div>
  <h2 class="display">How this <em>actually happens</em>.</h2>
  <p class="body wide">Start to finish, comparable venues have gone from first walkthrough to
  live screens in about thirty days. Nothing below asks the Arena for a dollar.</p>
  <div class="steps">{items}</div>
  {foot(11)}
</section>'''


def slide_12_thanks():
    def face(key, name):
        if key:
            return f'<div class="tm-face" style="background-image:url({HEADSHOTS[key]})"></div>'
        initials = "".join(w[0] for w in name.split()[:2])
        return f'<div class="tm-face tm-mono">{initials}</div>'

    team = "".join(
        f'<div class="tm">{face(k, n)}'
        f'<div class="tm-id"><div class="tm-n">{n}</div><div class="tm-r">{r}</div></div>'
        f'<div class="tm-c">{e}<br><span>{p}</span></div></div>'
        for n, r, e, p, k in TEAM)
    return f'''
<section class="slide cream">
  <div class="eyebrow">LET'S TALK</div>
  <h2 class="display">Thank you<br>for your <em>time</em>.</h2>
  <div class="two-col">
    <div class="col-left">
      <p class="body">Alli &mdash; thank you for having us out. If the concept works for you, the
      next move is a walkthrough at your convenience, and we'll bring a draft agreement to it.</p>
      <a class="cta">Schedule the walkthrough &rarr;</a>
      <div class="spec-card">
        <div class="spec-h">WHAT WE'D NEED FROM YOU</div>
        <div class="spec-l">Wall space and a standard power outlet at each screen</div>
        <div class="spec-l">Wi-Fi access for the media players (very light network use)</div>
        <div class="spec-l">A contact for content approval &mdash; and your event calendar</div>
      </div>
    </div>
    <div class="col-right">{team}</div>
  </div>
  <div class="foot"><span>MCTV DIGITAL, INC &middot; WWW.MCTVOFMS.COM</span><span class="pg">12</span></div>
</section>'''


SLIDES = [slide_01_cover(), slide_02_proposal(), slide_03_airport(), slide_04_network(),
          slide_05_footprint(), slide_06_placement(), slide_07_feed(), slide_07_package(),
          slide_08_revshare(), slide_09_events(), slide_10_whoweare(), slide_13_team(),
          slide_11_next(), slide_12_thanks()]


def numbered_slides(slides):
    """Stamp sequential page numbers so slides can be reordered without renumbering."""
    out = []
    for i, s in enumerate(slides, 1):
        out.append(s.replace("__PG__", f"{i:02d}"))
    return "".join(out)

CSS = f'''
*{{margin:0;padding:0;box-sizing:border-box}}
/* Chamber flip-book format: 11 x 6.5 in landscape, spiral bound.
   1280px wide keeps the type scale; 756px = 1280 * 6.5/11. */
@page{{size:11in 6.5in;margin:0}}
html,body{{background:#5a5a5a}}
body{{font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased}}
.slide{{width:1280px;height:756px;position:relative;overflow:hidden;
  page-break-after:always;break-after:page;padding:52px 70px 0}}
.slide:last-child{{page-break-after:auto}}
.cream{{background:{CREAM};color:{INK}}}
.navy{{background:{NAVY};color:#E7E3D8}}

.eyebrow{{font-size:10px;font-weight:600;letter-spacing:.24em;color:{RED};margin-bottom:15px}}
.eyebrow.gold{{color:{GOLD}}}
.display{{font-family:'Playfair Display',serif;font-weight:500;font-size:50px;
  line-height:1.08;letter-spacing:-.014em}}
.display em{{font-style:italic;color:{RED}}}
.navy .display em{{color:{GOLD}}}
.display.big{{font-size:46px;line-height:1.22}}
.display.sm{{font-size:28px}}

.body{{font-size:13.5px;line-height:1.92;color:#48546B;margin-bottom:17px;font-weight:400}}
.navy .body{{color:#B4BCCC}}
.body strong{{color:{INK};font-weight:600}}
.body.accent{{color:{RED}}} .navy .body.accent{{color:{GOLD}}}
.body.wide{{max-width:760px;margin-top:16px}}
.body.dim{{color:#96A0B2}}
.micro{{font-size:9px;line-height:1.75;color:#96A0B2;font-weight:400}}

.two-col{{display:flex;gap:62px;margin-top:30px}}
.two-col.wide-gap{{gap:86px}}
.col-left{{width:42%}} .col-right{{flex:1}} .pad-top{{padding-top:8px}}

.statrow{{position:absolute;left:70px;right:70px;bottom:74px;display:flex;gap:56px}}
.statrow.top{{position:static;margin:32px 0 6px}}
.statrow.bordered{{border-top:1px solid rgba(255,255,255,.14);padding-top:24px}}
.cream .statrow.bordered{{border-top-color:rgba(22,34,58,.14)}}
.stat-num{{font-family:'Playfair Display',serif;font-size:40px;font-weight:400;line-height:1}}
.stat-num.red{{color:{RED}}} .stat-num.gold{{color:{GOLD}}}
.stat-label{{font-size:8px;letter-spacing:.2em;font-weight:500;color:#96A0B2;margin-top:9px}}

.foot{{position:absolute;left:70px;right:70px;bottom:30px;display:flex;
  justify-content:space-between;font-size:8px;letter-spacing:.22em;
  font-weight:500;color:#A8B0BE}}
.navy .foot{{color:#5C6880}}
.pg{{font-family:'Playfair Display',serif;font-size:11px;letter-spacing:0}}

/* 01 cover */
.cover{{padding:0}}
.cover-glow{{position:absolute;width:980px;height:980px;right:-280px;bottom:-420px;
  background:radial-gradient(circle,rgba(194,161,92,.18) 0%,rgba(194,161,92,0) 62%)}}
.cover-rules{{position:absolute;inset:0;background:repeating-linear-gradient(
  90deg,rgba(255,255,255,.028) 0 1px,transparent 1px 96px)}}
.cover-logo{{position:absolute;left:70px;top:56px;width:140px;opacity:.96}}
.cover-tag{{position:absolute;right:70px;top:66px;font-size:8.5px;letter-spacing:.26em;
  font-weight:500;color:{GOLD}}}
.cover-body{{position:absolute;left:70px;bottom:186px}}
.cover-h1{{font-size:76px;line-height:1.06;color:#fff;letter-spacing:-.02em}}
.cover-sub{{margin-top:34px;font-size:9px;letter-spacing:.3em;font-weight:500;color:#8E99AD}}
.prepared{{position:absolute;right:70px;bottom:92px;text-align:right;
  border-right:2px solid {GOLD};padding-right:20px}}
.prepared-label{{font-size:8px;letter-spacing:.26em;color:{GOLD};font-weight:600}}
.prepared-name{{font-family:'Playfair Display',serif;font-size:27px;color:#fff;margin-top:8px}}
.prepared-org{{font-size:9px;letter-spacing:.09em;color:#8E99AD;margin-top:7px}}
.cover-foot{{bottom:44px;color:#5C6880}}

/* 02 numbered */
.num-item{{display:flex;gap:22px;margin-bottom:30px}}
.num-idx{{font-family:'Playfair Display',serif;font-size:21px;color:{RED};
  min-width:32px;padding-top:1px}}
.navy .num-idx{{color:{GOLD}}}
.num-title{{font-size:15.5px;font-weight:600;letter-spacing:-.005em;margin-bottom:8px}}
.num-body{{font-size:12.5px;line-height:1.82;color:#48546B}}
.navy .num-body{{color:#B4BCCC}}

/* 03 quote */
.quote-card{{background:rgba(255,255,255,.05);border-left:2px solid {GOLD};
  padding:30px 36px 28px;position:relative}}
.quote-mark{{font-family:'Playfair Display',serif;font-size:56px;color:{GOLD};
  line-height:.6;opacity:.5}}
.quote{{font-family:'Playfair Display',serif;font-size:21px;line-height:1.6;
  color:#F0EDE4;font-style:italic;margin:14px 0 22px}}
.quote-attr{{font-size:8px;letter-spacing:.2em;font-weight:600;color:{GOLD};line-height:1.9}}
.quote-attr span{{color:#5C6880;font-weight:500}}

/* 04 bars */
.cpm-head{{display:flex;justify-content:space-between;align-items:flex-end;
  margin-top:40px;gap:70px}}
.cpm-head .micro{{max-width:400px;text-align:right}}
.bars{{margin-top:26px}}
.bar-row{{display:flex;align-items:center;gap:20px;margin-bottom:13px}}
.bar-label{{width:180px;text-align:right;font-size:10.5px;font-weight:500;color:#5A6478}}
.bar-row.hi .bar-label{{color:{RED};font-weight:600}}
.bar-track{{flex:1}}
.bar{{height:27px;background:#E4DDCB;display:flex;align-items:center;padding-left:12px}}
.bar span{{font-size:9.5px;font-weight:600;color:#6B6250;letter-spacing:.04em}}
.bar-row.hi .bar{{background:{NAVY};min-width:96px}}
.bar-row.hi .bar span{{color:{GOLD}}}

/* 05 venues */
.chip-row{{display:flex;gap:16px;margin:28px 0 26px}}
.chip{{border:1px solid rgba(22,34,58,.16);padding:16px 32px 15px;min-width:158px}}
.chip.filled{{background:{NAVY};border-color:{NAVY}}}
.chip-num{{font-family:'Playfair Display',serif;font-size:32px;line-height:1}}
.chip.filled .chip-num{{color:#fff}}
.chip-label{{font-size:7.6px;letter-spacing:.19em;font-weight:500;color:#96A0B2;margin-top:8px}}
.chip.filled .chip-label{{color:{GOLD}}}
.venue-cols{{display:flex;gap:70px}}
.venue-col{{list-style:none;flex:1}}
.venue-col li{{font-size:10.5px;line-height:1;color:#54607A;padding:6.6px 0;
  border-bottom:1px solid rgba(22,34,58,.07)}}

/* 06 zones */
.zones{{display:flex;flex-wrap:wrap;gap:22px 52px;margin-top:30px}}
.zone{{display:flex;gap:18px;width:calc(50% - 26px)}}
.zone-i{{font-family:'Playfair Display',serif;font-size:17px;color:{GOLD};min-width:28px}}
.zone-t{{font-size:14px;font-weight:600;color:#EDEAE1;margin-bottom:6px}}
.zone-b{{font-size:11.5px;line-height:1.72;color:#96A0B2}}

/* 07 package cards */
.pkgs{{display:flex;gap:18px;margin-top:34px}}
.pkgs .pkg{{flex:1;background:rgba(255,255,255,.045);
  border-top:2px solid {GOLD};padding:24px 24px 26px}}
.pkg-h{{font-size:8.4px;letter-spacing:.19em;font-weight:600;color:{GOLD};min-height:24px}}
.pkg-p{{font-family:'Playfair Display',serif;font-size:38px;color:#fff;margin:6px 0 20px}}
.pkg-p span{{font-family:'Inter';font-size:9.5px;color:#7A869C;letter-spacing:.08em}}
.pkg-li{{font-size:11px;line-height:1.55;color:#B4BCCC;padding:9px 0;
  border-top:1px solid rgba(255,255,255,.08)}}
.pkg-foot{{position:absolute;left:70px;right:70px;bottom:70px;
  border-top:1px solid rgba(255,255,255,.14);padding-top:20px}}
.star{{color:{GOLD};font-size:17px;margin-right:10px}}
.pkg-foot-t{{font-family:'Playfair Display',serif;font-size:22px;color:#fff}}
.pkg-foot-b{{display:block;font-size:10.5px;color:#7A869C;letter-spacing:.03em;margin-top:9px}}

/* 08 econ table */
.econ{{width:100%;border-collapse:collapse;margin-bottom:20px}}
.econ th{{font-size:8px;letter-spacing:.16em;font-weight:600;color:#96A0B2;
  text-align:right;padding:0 0 13px;border-bottom:1px solid rgba(22,34,58,.16)}}
.econ th:first-child{{text-align:left}}
.econ td{{font-size:13.5px;text-align:right;padding:15px 0;color:#48546B;
  border-bottom:1px solid rgba(22,34,58,.07)}}
.econ td:first-child{{text-align:left;font-weight:500;color:{INK}}}
.econ td.hi{{font-family:'Playfair Display',serif;font-size:19px;color:{RED}}}

/* 09 feature */
.feature-card{{background:rgba(255,255,255,.05);border-left:2px solid {GOLD};padding:28px 34px}}
.feature-eyebrow{{font-size:8px;letter-spacing:.24em;font-weight:600;color:{GOLD}}}
.feature-t{{font-family:'Playfair Display',serif;font-size:27px;color:#fff;margin:12px 0 15px}}
.feature-b{{font-size:12.5px;line-height:1.82;color:#B4BCCC}}

/* 11 steps */
.steps{{display:flex;gap:26px;margin-top:44px}}
.step{{flex:1}}
.step-i{{font-family:'Playfair Display',serif;font-size:24px;color:{RED};margin-bottom:16px}}
.step-line{{height:1px;background:rgba(22,34,58,.16);margin-bottom:18px}}
.step-t{{font-size:13.5px;font-weight:600;line-height:1.4;margin-bottom:10px}}
.step-b{{font-size:11.5px;line-height:1.72;color:#6B7689}}

/* 12 thanks */
.cta{{display:inline-block;background:{RED};color:#fff;font-size:11px;font-weight:600;
  letter-spacing:.06em;padding:14px 26px;margin:8px 0 28px}}
.spec-card{{background:#EFEADC;padding:22px 26px}}
.spec-h{{font-size:8px;letter-spacing:.22em;font-weight:600;color:#8A8270;
  margin-bottom:12px}}
.spec-l{{font-size:11px;line-height:1.5;color:#5A6478;padding:8px 0;
  border-top:1px solid rgba(22,34,58,.08)}}
.tm{{display:flex;align-items:center;gap:18px;
  padding:14px 0;border-bottom:1px solid rgba(22,34,58,.1)}}
.tm:first-child{{padding-top:2px}}
.tm-id{{flex:1}}
.tm-face{{width:54px;height:54px;border-radius:50%;flex:none;
  background-size:cover;background-position:center 22%;
  box-shadow:0 0 0 1px rgba(22,34,58,.12)}}
.tm-mono{{display:flex;align-items:center;justify-content:center;background:#E7E1D2;
  font-family:'Playfair Display',serif;font-size:17px;color:#8A8270}}
.tm-n{{font-family:'Playfair Display',serif;font-size:20px}}
.tm-r{{font-size:8px;letter-spacing:.2em;font-weight:600;color:{RED};margin-top:5px}}
.tm-c{{font-size:10px;line-height:1.7;color:#7A8496;text-align:right}}
.tm-c span{{color:#96A0B2}}

/* ── Display mockups ─────────────────────────────────────────────────────
   Everything inside .screen is drawn in CSS. No photograph of the Arena is
   implied anywhere in this deck — see the photo() slots to add real ones. */
.screen{{margin-top:6px}}
.bezel{{position:relative;background:linear-gradient(160deg,#2B3038,#15181D 60%);
  padding:9px 9px 13px;border-radius:5px;
  box-shadow:0 18px 34px rgba(0,0,0,.34),0 1px 0 rgba(255,255,255,.13) inset}}
.panel{{position:relative;aspect-ratio:16/9;overflow:hidden;background:#0a1220}}
.gloss{{position:absolute;inset:9px 9px 13px;pointer-events:none;border-radius:2px;
  background:linear-gradient(103deg,rgba(255,255,255,.10) 0%,
    rgba(255,255,255,.03) 22%,rgba(255,255,255,0) 48%)}}
.mount{{width:74px;height:9px;margin:0 auto;border-radius:0 0 4px 4px;
  background:linear-gradient(#22262C,#15181D)}}
.screen-cap{{margin-top:13px;font-size:7.4px;letter-spacing:.2em;font-weight:600;
  color:#7A869C;text-align:center}}
.cream .screen-cap{{color:#96A0B2}}
.screen.sm{{max-width:252px;margin-top:14px}}
.screen.sm .bezel{{padding:6px 6px 9px}} .screen.sm .mount{{width:52px;height:7px}}
.screen.sm .screen-cap{{margin-top:9px;font-size:6.4px;letter-spacing:.16em}}

/* sample Arena spot */
.spot{{position:absolute;inset:0;background:
  radial-gradient(120% 100% at 84% 8%,#1D2A16 0%,#0E1408 58%,#080B05 100%);
  padding:6.4% 7%;display:flex;flex-direction:column;justify-content:space-between}}
.spot-top{{display:flex;justify-content:space-between;align-items:center}}
.spot-mark{{font-size:6.2px;letter-spacing:.24em;font-weight:700;color:{HBA_GREEN}}}
.spot-live{{font-size:5.6px;letter-spacing:.2em;font-weight:700;color:#0C1206;
  background:{HBA_GREEN};padding:3px 7px;border-radius:2px}}
.spot-kicker{{font-size:6.4px;letter-spacing:.22em;font-weight:600;color:#9FB08C}}
.spot-title{{font-family:'Playfair Display',serif;font-size:31px;color:#fff;
  line-height:1;margin:7px 0 8px;letter-spacing:-.015em}}
.spot-sub{{font-size:6.6px;letter-spacing:.2em;font-weight:600;color:{HBA_GREEN}}}
.spot-rule{{height:1px;background:linear-gradient(90deg,{HBA_GREEN},rgba(141,198,63,0))}}
.spot-foot{{display:flex;justify-content:space-between;align-items:center;
  font-size:5.8px;letter-spacing:.2em;font-weight:600;color:#7E8C6E;margin-top:7px}}
.spot-mctv{{color:#fff;letter-spacing:.3em;font-weight:700}}

/* lobby event board — mirrors static/board.html */
.board{{position:absolute;inset:0;padding:3.4% 3.6%;color:#fff;font-size:10px;
  background:radial-gradient(120% 90% at 12% 0%,#101c2e 0%,#0a1220 62%);
  display:flex;flex-direction:column}}
.bhead{{display:flex;justify-content:space-between;align-items:flex-start;
  padding-bottom:2.4%;border-bottom:1px solid rgba(255,255,255,.10)}}
.bvenue{{font-size:12.5px;font-weight:700;letter-spacing:-.01em}}
.btag{{font-size:6px;font-weight:700;letter-spacing:.2em;color:#d4a017;margin-top:3px}}
.bclock{{text-align:right}}
.btime-now{{font-size:16px;font-weight:700;line-height:1}}
.btime-now span{{font-size:7.5px;font-weight:700;color:#8fa2b8;margin-left:3px}}
.bdate{{font-size:6.2px;font-weight:600;color:#8fa2b8;margin-top:4px}}
.bnowlbl{{display:flex;align-items:center;gap:5px;font-size:6px;font-weight:700;
  letter-spacing:.2em;color:#d4a017;margin:2.4% 0 1.2%}}
.bdot{{width:5px;height:5px;border-radius:50%;background:#3fbf6a;flex:none}}
.bnow{{display:flex;gap:4%;padding:2.4% 3.4%;border-radius:2px;
  background:linear-gradient(100deg,rgba(212,160,23,.16) 0%,rgba(212,160,23,.05) 60%);
  border-left:2px solid #d4a017}}
.bnow-when{{font-size:11px;font-weight:700;min-width:82px}}
.bnow-r{{font-size:6px;font-weight:700;color:#d4a017;margin-top:3px;letter-spacing:.1em}}
.bnow-n{{font-size:11.5px;font-weight:700}}
.bnow-o{{font-size:6.4px;font-weight:600;color:#8fa2b8;margin-top:3px}}
.bnextlbl{{display:flex;justify-content:space-between;font-size:6px;font-weight:700;
  letter-spacing:.2em;color:#8fa2b8;margin:2.4% 0 1.1%}}
.bpage{{color:#5e7189;letter-spacing:.12em}}
.brow{{display:flex;align-items:center;gap:3.4%;padding:1.5% 3.4%;margin-bottom:0.8%;
  background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.10);border-radius:2px}}
.btime{{font-size:8.4px;font-weight:700;min-width:52px}}
.btitle{{flex:1}}
.bn{{font-size:8.6px;font-weight:700}}
.bo{{font-size:6px;font-weight:600;color:#8fa2b8;margin-top:2px}}
.broom{{font-size:6.6px;font-weight:800;color:#d4a017;text-align:right;letter-spacing:.08em}}
.brow.soon{{border-color:rgba(212,160,23,.45);background:rgba(212,160,23,.07)}}
.brow.private .bn{{color:#8fa2b8;font-style:italic;font-weight:600}}
.bbrand{{margin-top:auto;padding-top:2.4%;display:flex;justify-content:space-between;
  font-size:5.6px;font-weight:600;color:#5e7189;letter-spacing:.14em}}
.bbrand b{{color:#fff;font-weight:800}} .bbrand b span{{color:#d4a017}}

/* 07 the feed grid */
.fgrid{{display:flex;gap:18px;margin-top:38px}}
.fcell{{flex:1}}
.screen.xs .bezel{{padding:5px 5px 7px}} .screen.xs .mount{{width:40px;height:5px}}
.screen.xs .screen-cap{{margin-top:8px;font-size:6.2px;letter-spacing:.16em}}
.feed{{position:absolute;inset:0;padding:7% 7.5%;display:flex;flex-direction:column;
  color:#fff;background:radial-gradient(120% 100% at 15% 0%,#16233c 0%,#0a1220 65%)}}
.feed-top{{display:flex;justify-content:space-between;align-items:center;
  font-size:5.4px;letter-spacing:.2em;font-weight:600;color:#5e7189;margin-bottom:9%}}
.feed-lbl{{color:{GOLD}}}
.wx-now{{display:flex;align-items:center;gap:9%}}
.wx-temp{{font-family:'Playfair Display',serif;font-size:38px;line-height:.9}}
.wx-cond{{font-size:9px;font-weight:600}}
.wx-meta{{font-size:5.8px;color:#8fa2b8;margin-top:3px;font-weight:500}}
.wx-week{{display:flex;gap:4%;margin-top:auto;padding-top:6%;
  border-top:1px solid rgba(255,255,255,.10)}}
.wx-d{{flex:1;text-align:center}}
.wx-dn{{font-size:5.2px;letter-spacing:.16em;font-weight:700;color:#8fa2b8}}
.wx-hi{{font-size:10px;font-weight:700;margin-top:4px}}
.wx-lo{{font-size:6px;color:#5e7189;font-weight:600}}
.nw-lead{{font-family:'Playfair Display',serif;font-size:15px;line-height:1.2;
  padding-bottom:6%;border-bottom:1px solid rgba(255,255,255,.10)}}
.nw-rows{{margin-top:6%}}
.nw-r{{font-size:6.6px;font-weight:500;color:#c8d0dd;padding:3.4% 0;display:flex;gap:8px}}
.nw-r span{{color:{GOLD};font-weight:700;font-size:5.2px;letter-spacing:.14em;
  min-width:34px;padding-top:1px}}
.tv-q{{font-family:'Playfair Display',serif;font-size:13px;line-height:1.42;
  font-style:italic;color:#F0EDE4}}
.tv-a{{margin-top:auto;font-size:5.6px;letter-spacing:.18em;font-weight:700;color:{GOLD}}}

/* 13 team cards */
.tcards{{display:flex;gap:34px;margin-top:52px}}
.tcard{{flex:1;text-align:center}}
.tface{{width:176px;height:176px;border-radius:50%;margin:0 auto 20px;
  background-size:cover;background-position:center 20%;
  box-shadow:0 0 0 1px rgba(22,34,58,.12),0 10px 26px rgba(22,34,58,.14)}}
.tname{{font-family:'Playfair Display',serif;font-size:22px}}
.trole{{font-size:8px;letter-spacing:.2em;font-weight:600;color:{RED};margin-top:8px}}
.tcontact{{font-size:10px;line-height:1.75;color:#7A8496;margin-top:12px}}

/* their branding — a co-brand rule on the cover, in the Arena's own green */
.cobrand{{position:absolute;left:70px;bottom:130px;display:flex;align-items:center;gap:18px}}
.cobrand-bar{{width:34px;height:2px;background:{HBA_GREEN}}}
.cobrand-t{{font-size:8px;letter-spacing:.26em;font-weight:600;color:{HBA_GREEN}}}

/* cover photography (only when photos/cover.* is present) */
.cover-photo{{position:absolute;inset:0;background-size:cover;background-position:center}}
.cover-scrim{{position:absolute;inset:0;background:
  linear-gradient(96deg,rgba(10,17,32,.94) 0%,rgba(10,17,32,.80) 38%,rgba(10,17,32,.30) 100%)}}
.photo-card{{position:relative;overflow:hidden}}
.photo-card img{{width:100%;display:block}}
.photo-cap{{position:absolute;left:0;right:0;bottom:0;padding:11px 16px;
  background:linear-gradient(rgba(10,17,32,0),rgba(10,17,32,.88));
  font-size:7.4px;letter-spacing:.2em;font-weight:600;color:#E7E3D8}}
'''

HTML = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>MCTV Host Media Kit &mdash; {VENUE}</title>
<style>{FONTS}</style><style>{CSS}</style></head>
<body>{numbered_slides(SLIDES)}</body></html>'''


def main():
    html_path = HERE / "deck.html"
    html_path.write_text(HTML, encoding="utf-8")
    print(f"wrote {html_path}  ({html_path.stat().st_size // 1024} KB)")

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    candidates = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    candidates += [pathlib.Path("/usr/bin/chromium"), pathlib.Path("/usr/bin/google-chrome")]
    chrome = next((str(c) for c in candidates if c.exists()), None)
    if chrome is None:
        sys.exit("no chromium binary found")
    cmd = [chrome, "--headless", "--disable-gpu", "--no-sandbox",
           "--run-all-compositor-stages-before-draw",
           "--virtual-time-budget=12000",
           f"--print-to-pdf={OUT_PDF}", "--no-pdf-header-footer",
           f"file://{html_path}"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not OUT_PDF.exists():
        print(res.stdout, res.stderr, file=sys.stderr)
        sys.exit("PDF render failed")
    print(f"wrote {OUT_PDF}  ({OUT_PDF.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
