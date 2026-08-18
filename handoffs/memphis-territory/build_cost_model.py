#!/usr/bin/env python3
"""Render the DeSoto build cost calculator.

Interactive rather than a static report: every input is a published figure or an
estimate, and the ones that matter most are the ones only Creed can confirm. Emits
a standalone page for the repo and a fragment for the Artifact publisher.
"""

ROOT = "/home/user/mctv-bot"
OUT = f"{ROOT}/handoffs/memphis-territory"
PAGE_TITLE = "MCTV &mdash; DeSoto Build Cost Model"

CSS = """
  :root { --navy:#1B1F3B; --gold:#C5A55A; --bg:#f7f7f9; --card:#fff; --text:#1a1a1a;
          --muted:#5d616b; --line:#e3e3e8; --field:#f2f3f6;
          --good:#4F8A57; --warn:#C4576B; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6; --line:#2a2f36;
            --field:#0e131a; }
  }
  :root[data-theme="dark"] { --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6;
                             --line:#2a2f36; --field:#0e131a; }
  :root[data-theme="light"] { --bg:#f7f7f9; --card:#fff; --text:#1a1a1a; --muted:#5d616b;
                              --line:#e3e3e8; --field:#f2f3f6; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:Arial,Helvetica,sans-serif; background:var(--bg); color:var(--text);
         line-height:1.55; }
  header.top { background:var(--navy); color:#fff; padding:34px 24px; border-bottom:5px solid var(--gold); }
  header.top h1 { margin:0 0 6px; font-size:27px; text-wrap:balance; }
  header.top p { margin:0; color:#c9cbd6; font-size:14px; }
  .badge-int { display:inline-block; margin-top:12px; background:#C4576B; color:#fff; font-size:11px;
               letter-spacing:.8px; text-transform:uppercase; padding:4px 10px; font-weight:bold; }
  .wrap { max-width:1140px; margin:0 auto; padding:24px; }
  h2 { font-size:19px; margin:34px 0 12px; padding-bottom:8px; border-bottom:2px solid var(--gold);
       text-wrap:balance; }
  .callout { background:var(--card); border:1px solid var(--line); border-left:4px solid var(--navy);
             padding:15px 19px; font-size:13.5px; margin-bottom:18px; }
  .callout.gap { border-left-color:var(--warn); }
  .callout.key { border-left-color:var(--gold); }
  .callout b { color:var(--gold); }
  .grid2 { display:grid; grid-template-columns:minmax(280px,1fr) minmax(320px,1.4fr); gap:20px;
           align-items:start; }
  @media (max-width:820px) { .grid2 { grid-template-columns:1fr; } }
  fieldset { border:1px solid var(--line); background:var(--card); padding:14px 16px 16px;
             margin:0 0 16px; }
  legend { font-size:11px; text-transform:uppercase; letter-spacing:.8px; color:var(--muted);
           font-weight:bold; padding:0 6px; }
  .row { display:flex; align-items:center; gap:10px; margin-bottom:9px; }
  .row label { flex:1; font-size:13px; }
  .row input { width:104px; padding:6px 8px; font:inherit; font-size:13px; text-align:right;
    background:var(--field); color:var(--text); border:1px solid var(--line);
    font-variant-numeric:tabular-nums; }
  .row input:focus-visible { outline:3px solid var(--gold); outline-offset:1px; }
  .row .unit { font-size:11px; color:var(--muted); width:34px; }
  .src { font-size:11px; color:var(--muted); margin:8px 0 0; }
  .tablewrap { overflow-x:auto; }
  table { border-collapse:collapse; width:100%; background:var(--card); border:1px solid var(--line);
          font-size:13px; min-width:520px; margin-bottom:16px; }
  th,td { padding:9px 12px; border-bottom:1px solid var(--line); text-align:right; }
  th:first-child, td:first-child { text-align:left; }
  td { font-variant-numeric:tabular-nums; }
  th { background:var(--navy); color:#fff; font-size:11px; text-transform:uppercase;
       letter-spacing:.6px; }
  tr:last-child td { border-bottom:none; }
  tbody tr.total td { font-weight:bold; border-top:2px solid var(--gold); }
  .be { color:var(--gold); font-weight:bold; }
  .stats { display:flex; flex-wrap:wrap; gap:12px; margin:0 0 16px; }
  .stat { background:var(--card); border:1px solid var(--line); border-left:4px solid var(--gold);
          padding:11px 15px; min-width:158px; flex:1; }
  .stat b { display:block; font-size:22px; color:var(--gold); font-variant-numeric:tabular-nums; }
  .stat span { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.6px; }
  .stat.warnbox { border-left-color:var(--warn); }
  .stat.warnbox b { color:var(--warn); }
  footer { padding:30px 24px; text-align:center; color:var(--muted); font-size:12px; }
"""

BODY = """<header class="top">
  <h1>What the Territory Actually Costs</h1>
  <p>DeSoto County build model &middot; MCTV Elite Advertising &middot; every input is editable</p>
  <span class="badge-int">Internal &mdash; not for n-Compass</span>
</header>
<div class="wrap">

  <div class="callout key">
    <b>The territory carries a $50,000 price, and Don is willing to waive it.</b> That is a real
    gift &mdash; and it is still not the number that decides this.
    <br><br>
    The ongoing royalty is <b>$500/month flat plus $75 per billboard per month</b>. At 90 DeSoto
    screens that is roughly <b>$87,000 every year, forever</b> &mdash; about <b>$435,000 over five
    years</b>.
    <br><br>
    <b>So the gift is about 11% of what the territory costs to hold for five years.</b> Entry is
    free; occupancy is not. Negotiate the royalty and the build-out clause, not the entry price
    &mdash; the entry price is already zero.
  </div>

  <div class="callout gap">
    <b>The question that actually matters: what comes with it?</b> Three very different deals wear
    the same &ldquo;territory&rdquo; label, and the price being zero does not tell us which one this
    is.
    <ul>
      <li><b>Rights only</b> &mdash; we build all 90 screens ourselves from zero. That is the model
        below, and it is still a good deal at $0 entry.</li>
      <li><b>Rights + her installed screens</b> (~32&ndash;35 of them) &mdash; roughly $20,000 of
        hardware we do not buy, plus host agreements already signed, which is the slow part of any
        build. Set <b>screens inherited</b> below to model it.</li>
      <li><b>Rights + screens + her advertiser contracts</b> &mdash; then it is not a territory
        handover at all, it is an <b>acquisition arriving for free</b>. If she has 15 advertisers at
        even $400/month, that is $72,000 a year of revenue walking in the door, and it changes the
        ramp completely &mdash; we would start with a book instead of an empty network.</li>
    </ul>
    <b>Ask which one it is.</b> And if a book of business comes with it, ask what it earns &mdash;
    that is the difference between a 5-month payback and starting cash-flow positive.
  </div>

  <div class="callout gap">
    <b>Verify this against our own agreement before using it.</b> These are n-Compass's published
    <i>franchise</i> terms. We already run 133 screens on NTV360, so we may be on dealer terms,
    grandfathered terms, or a different per-screen rate entirely &mdash; and if so the published
    figures do not apply to us. Override the royalty inputs below with our real numbers.
    <br><br>
    This also adds a fifth question for Don: <b>does the DeSoto territory come under our existing
    agreement, or a new one?</b> Waiving $50,000 of entry while attaching $75/screen/month to 90 new
    screens is a discounted signup on a subscription, not a free lunch. Both can be worth it &mdash;
    but we should know which deal we are signing.
  </div>

  <h2>Model</h2>
  <div class="grid2">
    <div>
      <fieldset>
        <legend>One time &mdash; entry</legend>
        <div class="row"><label for="terr">Territory cost (waived)</label>
          <input id="terr" type="number" value="0" min="0" step="5000"><span class="unit">$</span></div>
        <div class="row"><label for="inherit">Screens inherited in the deal</label>
          <input id="inherit" type="number" value="0" min="0" step="1"><span class="unit">#</span></div>
        <p class="src">Listed at $50,000; Don is willing to waive it, so the default is $0. Put the
        $50,000 back to see what it would cost if the terms change. Set <b>screens inherited</b>
        above zero if her installed base comes with it &mdash; those come off our build.</p>
      </fieldset>

      <fieldset>
        <legend>Per screen &mdash; one time</legend>
        <div class="row"><label for="hw">Display + media player</label>
          <input id="hw" type="number" value="450" min="0" step="25"><span class="unit">$</span></div>
        <div class="row"><label for="inst">Mount + installation</label>
          <input id="inst" type="number" value="150" min="0" step="25"><span class="unit">$</span></div>
        <p class="src">Industry range for a fully installed commercial screen is $1,800&ndash;$3,500,
        but that assumes large commercial-grade panels. Our venue screens are smaller consumer/
        light-commercial units, so the default sits well below it. Raise it if we spec up.</p>
      </fieldset>

      <fieldset>
        <legend>Per screen &mdash; monthly</legend>
        <div class="row"><label for="roy">n-Compass royalty per screen</label>
          <input id="roy" type="number" value="75" min="0" step="5"><span class="unit">$</span></div>
        <div class="row"><label for="conn">Connectivity / data</label>
          <input id="conn" type="number" value="15" min="0" step="5"><span class="unit">$</span></div>
        <p class="src">$75 is n-Compass's published per-billboard royalty. This is the single most
        important input on the page &mdash; replace it with our actual rate.</p>
      </fieldset>

      <fieldset>
        <legend>Fixed monthly</legend>
        <div class="row"><label for="flat">n-Compass flat fee</label>
          <input id="flat" type="number" value="500" min="0" step="50"><span class="unit">$</span></div>
        <div class="row"><label for="rep">Rep cost (base + comm)</label>
          <input id="rep" type="number" value="4500" min="0" step="250"><span class="unit">$</span></div>
        <p class="src">90 screens across DeSoto is not a remote-managed market. The rep is a real
        line item, not an afterthought.</p>
      </fieldset>

      <fieldset>
        <legend>Sell-through</legend>
        <div class="row"><label for="adv">Advertisers sold (steady state)</label>
          <input id="adv" type="number" value="20" min="0" step="1"><span class="unit">#</span></div>
        <p class="src">Revenue is advertisers sold, not screens hung. Screens are inventory; the
        rate card charges per advertiser by network size.</p>
      </fieldset>
    </div>

    <div>
      <div class="stats" id="headline"></div>
      <div class="tablewrap"><table id="phases">
        <thead><tr>
          <th>Phase</th><th>Screens</th><th>Tier</th><th>Capex</th>
          <th>Monthly cost</th><th>Break-even</th>
        </tr></thead>
        <tbody></tbody>
      </table></div>

      <div class="tablewrap"><table id="detail">
        <thead><tr><th>At full build (Phase 3)</th><th>Monthly</th><th>Annual</th></tr></thead>
        <tbody></tbody>
      </table></div>
    </div>
  </div>

  <h2>How to read it</h2>
  <div class="callout">
    <b>Break-even is in advertisers, not dollars.</b> It is the number of advertisers we must have
    under contract, at that phase's rate, before the DeSoto operation stops losing money each month.
    Watch what happens to it between Phase 1 and Phase 2: the screen count nearly doubles, but
    break-even barely moves &mdash; because crossing 75 screens lifts the rate card from $800 to
    $1,300 per advertiser. <b>Revenue per advertiser rises faster than cost per screen.</b> That is
    the whole argument for phasing to the tier lines rather than stopping short of them.
  </div>
  <div class="callout">
    <b>Entry is the small problem &mdash; and it is now zero.</b> The hardware build alone lands
    inside the $48,150&ndash;$120,405 range n-Compass publishes for a new franchise, which is a
    decent sanity check on the per-screen defaults.
    <br><br>
    With entry waived, <b>everything that matters in this deal is recurring or contractual</b>: the
    royalty rate, the build-out clause, and whether we get exclusivity. Those are the three things
    to negotiate. The $50,000 is already won.
  </div>

</div>
<footer>MCTV Digital, Inc. &mdash; internal planning model. Figures are estimates; confirm against
our n-Compass agreement.</footer>
<script>
(function () {
  const TIERS = [
    { screens: 10, rate: 350 }, { screens: 20, rate: 500 },
    { screens: 40, rate: 800 }, { screens: 75, rate: 1300 }
  ];
  const PHASES = [
    { name: 'Phase 1 — Olive Branch + Hernando', screens: 40 },
    { name: 'Phase 2 — + Southaven', screens: 75 },
    { name: 'Phase 3 — + Horn Lake / Walls / Nesbit', screens: 90 }
  ];
  const ids = ['terr', 'inherit', 'hw', 'inst', 'roy', 'conn', 'flat', 'rep', 'adv'];
  const $ = id => document.getElementById(id);
  const money = n => '$' + Math.round(n).toLocaleString('en-US');

  function rateFor(screens) {
    let r = 0;
    for (const t of TIERS) if (screens >= t.screens) r = t.rate;
    return r;
  }

  function render() {
    const v = {};
    ids.forEach(id => { v[id] = Number($(id).value) || 0; });
    const perScreenCapex = v.hw + v.inst;
    const perScreenMonthly = v.roy + v.conn;
    const fixed = v.flat + v.rep;

    const body = document.querySelector('#phases tbody');
    body.innerHTML = '';
    let prev = 0;
    let last = null;
    let inheritLeft = v.inherit;
    for (const p of PHASES) {
      const rate = rateFor(p.screens);
      const added = p.screens - prev;
      // Inherited screens absorb the earliest phases first.
      const free = Math.min(inheritLeft, added);
      inheritLeft -= free;
      const capex = (added - free) * perScreenCapex + (prev === 0 ? v.terr : 0);
      const monthly = fixed + p.screens * perScreenMonthly;
      const be = Math.ceil(monthly / rate);
      last = { p, rate, monthly, cumCapex: (last ? last.cumCapex : 0) + capex };
      body.insertAdjacentHTML('beforeend',
        `<tr><td>${p.name}</td><td>${p.screens}</td><td>${money(rate)}/mo</td>` +
        `<td>${money(capex)}</td><td>${money(monthly)}</td>` +
        `<td class="be">${be} advertisers</td></tr>`);
      prev = p.screens;
    }

    const s = PHASES[PHASES.length - 1].screens;
    const rate = rateFor(s);
    const royalty = s * v.roy + v.flat;
    const monthly = fixed + s * perScreenMonthly;
    const revenue = v.adv * rate;
    const margin = revenue - monthly;
    const totalCapex = Math.max(s - v.inherit, 0) * perScreenCapex + v.terr;

    const det = document.querySelector('#detail tbody');
    const line = (label, m) =>
      `<tr><td>${label}</td><td>${money(m)}</td><td>${money(m * 12)}</td></tr>`;
    det.innerHTML =
      line('n-Compass royalty (' + s + ' × ' + money(v.roy) + ' + ' + money(v.flat) + ' flat)', royalty) +
      line('Connectivity', s * v.conn) +
      line('Rep', v.rep) +
      `<tr class="total"><td>Total cost</td><td>${money(monthly)}</td><td>${money(monthly * 12)}</td></tr>` +
      line(v.adv + ' advertisers × ' + money(rate), revenue) +
      `<tr class="total"><td>Margin</td><td>${money(margin)}</td><td>${money(margin * 12)}</td></tr>`;

    const payback = margin > 0 ? Math.ceil(totalCapex / margin) : null;
    const be = Math.ceil(monthly / rate);
    document.getElementById('headline').innerHTML =
      `<div class="stat"><b>${money(totalCapex)}</b><span>All-in to 90 screens</span></div>` +
      `<div class="stat warnbox"><b>${money(royalty * 12)}</b><span>n-Compass, per year</span></div>` +
      `<div class="stat"><b>${be}</b><span>Break-even advertisers</span></div>` +
      `<div class="stat"><b>${payback ? payback + ' mo' : '—'}</b><span>Capex payback</span></div>` +
      `<div class="stat"><b>${money(margin)}</b><span>Monthly margin at ${v.adv}</span></div>`;
  }

  ids.forEach(id => $(id).addEventListener('input', render));
  render();
})();
</script>
"""

html = (
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    f"<title>{PAGE_TITLE}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
    + BODY + "</body>\n</html>\n"
)
artifact_html = f"<title>{PAGE_TITLE}</title>\n<style>{CSS}</style>\n" + BODY

with open(f"{OUT}/cost-model.html", "w") as f:
    f.write(html)
with open(f"{OUT}/cost-model.artifact.html", "w") as f:
    f.write(artifact_html)

print(f"cost-model.html written: {len(html):,} bytes")
