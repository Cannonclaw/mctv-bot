// Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
// Proprietary and confidential. Unauthorized copying, distribution,
// or modification of this file is strictly prohibited.
//
// FNB Oxford Bank — "Grow With Us" $10K upsell deck (MCTV Elite Advertising)
// Turns the traction-report numbers in fnb_data.json into an 11-slide branded
// PowerPoint. To reuse for another client, copy fnb_data.json, swap in that
// client's report numbers, and pass it as the first argument.
//
// Usage: node build_deck.js [data.json] [assets_dir] [out.pptx]
// Requires: npm install pptxgenjs

const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const REPO_ROOT = path.join(__dirname, "..", "..");
const DATA = JSON.parse(fs.readFileSync(process.argv[2] || path.join(__dirname, "fnb_data.json"), "utf8"));
const ASSETS = process.argv[3] || path.join(REPO_ROOT, "assets");
const OUT = process.argv[4] || path.join(REPO_ROOT, "output", "decks", "FNB_GrowWithUs_10K_Deck.pptx");
fs.mkdirSync(path.dirname(OUT), { recursive: true });

// MCTV "Original" scheme (docx_service.py)
const NAVY = "1B1F3B";
const NAVY_CARD = "262B4D";   // card fill on navy slides
const GOLD = "C5A55A";
const GOLD_DARK = "A8873D";   // small gold text on white
const WHITE = "FFFFFF";
const LIGHT = "F4F5F7";       // card fill on white slides
const INK = "23273D";         // body text on light
const MUTED = "70758A";
const ICE = "C9CDE0";         // muted text on navy
const FONT = "Arial";

const W = 13.333, H = 7.5, MARGIN = 0.75;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "MCTV Elite Advertising";
pres.title = "FNB × MCTV — Grow With Us";

const logoWhite = path.join(ASSETS, "branding/mctv_logo_white.png");
const logoLight = path.join(ASSETS, "branding/mctv_logo_on_light.png");
const LOGO_AR = 934 / 283; // logo aspect ratio

function goldSq(slide, x, y, size) {
  slide.addShape("rect", { x, y, w: size || 0.14, h: size || 0.14, fill: { color: GOLD } });
}

function footer(slide, page, dark) {
  slide.addText(`MCTV Elite Advertising  |  FNB Growth Plan  |  ${page}`, {
    x: MARGIN, y: 7.08, w: W - 2 * MARGIN, h: 0.3, align: "right",
    fontFace: FONT, fontSize: 9, color: dark ? ICE : MUTED, margin: 0,
  });
}

function titleBlock(slide, kicker, title, dark) {
  goldSq(slide, MARGIN, 0.62, 0.14);
  slide.addText(kicker.toUpperCase(), {
    x: MARGIN + 0.26, y: 0.47, w: 9, h: 0.42, fontFace: FONT, fontSize: 12,
    color: dark ? GOLD : GOLD_DARK, charSpacing: 3, bold: true, margin: 0, valign: "middle",
  });
  slide.addText(title, {
    x: MARGIN, y: 0.92, w: W - 2 * MARGIN, h: 0.85, fontFace: FONT, fontSize: 32,
    bold: true, color: dark ? WHITE : NAVY, margin: 0, valign: "top",
  });
}

// ───────────────────────── Slide 1 — Cover (navy) ─────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  const lw = 2.5;
  s.addImage({ path: logoWhite, x: MARGIN, y: 0.7, w: lw, h: lw / LOGO_AR });

  goldSq(s, MARGIN, 2.78, 0.2);
  s.addText("GROW WITH US.", {
    x: MARGIN, y: 3.0, w: 11.8, h: 1.15, fontFace: FONT, fontSize: 60, bold: true,
    color: WHITE, margin: 0,
  });
  s.addText(`${DATA.client}  ×  MCTV Elite Advertising`, {
    x: MARGIN, y: 4.22, w: 11.8, h: 0.5, fontFace: FONT, fontSize: 20, color: GOLD, bold: true, margin: 0,
  });
  s.addText("Six months of results — and the plan for what comes next.", {
    x: MARGIN, y: 4.76, w: 11.8, h: 0.45, fontFace: FONT, fontSize: 15, color: ICE, margin: 0,
  });

  s.addText([
    { text: `Campaign results: ${DATA.period}`, options: { breakLine: true } },
    { text: "Prepared by T. Creed Cannon  |  creed@mctvofms.com  |  (601) 201-8202", options: {} },
  ], {
    x: MARGIN, y: 6.42, w: 11.8, h: 0.7, fontFace: FONT, fontSize: 11.5, color: ICE,
    margin: 0, lineSpacingMultiple: 1.35,
  });
}

// ───────────────── Slide 2 — KPI grid: six months in (white) ─────────────────
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  titleBlock(s, "Your results · " + DATA.period, "Six months in. Here's what FNB got.");

  const k = DATA.kpis;
  const tiles = [
    [k.total_plays, "Total ad plays"],
    [k.active_venues, "Active venues"],
    [k.screen_time, "Hours on screen"],
    [k.monthly_impressions, "Est. monthly impressions"],
    [k.network_cpm, "Network CPM"],
    [k.avg_dwell, "Average dwell time"],
  ];
  const tw = 3.75, th = 1.92, gx = 0.29, gy = 0.32, x0 = MARGIN, y0 = 2.05;
  tiles.forEach(([num, label], i) => {
    const x = x0 + (i % 3) * (tw + gx), y = y0 + Math.floor(i / 3) * (th + gy);
    s.addShape("roundRect", { x, y, w: tw, h: th, fill: { color: LIGHT }, rectRadius: 0.06, line: { type: "none" } });
    goldSq(s, x + 0.3, y + 0.32, 0.12);
    s.addText(num, {
      x: x + 0.3, y: y + 0.52, w: tw - 0.6, h: 0.75, fontFace: FONT, fontSize: 34,
      bold: true, color: NAVY, margin: 0, valign: "middle",
    });
    s.addText(label.toUpperCase(), {
      x: x + 0.3, y: y + 1.32, w: tw - 0.6, h: 0.35, fontFace: FONT, fontSize: 10.5,
      color: MUTED, charSpacing: 2, margin: 0,
    });
  });

  s.addText("Real hours in front of real people, in the places they already spend their time.  ·  Source: NTV360 network analytics",
    { x: MARGIN, y: 6.55, w: W - 2 * MARGIN, h: 0.35, fontFace: FONT, fontSize: 11.5, italic: true, color: MUTED, margin: 0 });
  footer(s, 2);
}

// ───────────── Slide 3 — Top venues + markets (white, table) ─────────────
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  titleBlock(s, "Where you showed up", "65 venues carried the FNB name every day.");

  const rows = [
    [
      { text: "TOP VENUES", options: { bold: true, color: WHITE, fill: { color: NAVY } } },
      { text: "CITY", options: { bold: true, color: WHITE, fill: { color: NAVY } } },
      { text: "PLAYS", options: { bold: true, color: WHITE, fill: { color: NAVY }, align: "right" } },
      { text: "CPM", options: { bold: true, color: WHITE, fill: { color: NAVY }, align: "right" } },
    ],
  ];
  DATA.top_venues.forEach((v, i) => {
    const fill = { color: i % 2 ? LIGHT : WHITE };
    const bold = i === 0;
    rows.push([
      { text: v.name, options: { fill, bold, color: INK } },
      { text: v.city, options: { fill, color: MUTED } },
      { text: v.plays, options: { fill, bold, color: INK, align: "right" } },
      { text: v.cpm, options: { fill, color: INK, align: "right" } },
    ]);
  });
  s.addTable(rows, {
    x: MARGIN, y: 2.05, w: 6.9, colW: [3.4, 1.1, 1.3, 1.1],
    fontFace: FONT, fontSize: 11, rowH: 0.42, valign: "middle",
    border: { type: "solid", color: "E3E5EC", pt: 0.5 },
  });

  s.addText("Oxford Park Commission alone out-played your next two venues combined.", {
    x: MARGIN, y: 5.72, w: 6.9, h: 0.6, fontFace: FONT, fontSize: 11.5, italic: true, color: MUTED, margin: 0,
  });

  // Market cards, right column
  const mx = 8.05, mw = 4.53;
  DATA.markets_current.forEach((m, i) => {
    const y = 2.05 + i * 1.45;
    s.addShape("roundRect", { x: mx, y, w: mw, h: 1.22, fill: { color: LIGHT }, rectRadius: 0.06, line: { type: "none" } });
    s.addText(m.name.toUpperCase(), { x: mx + 0.3, y: y + 0.16, w: mw - 0.6, h: 0.32, fontFace: FONT, fontSize: 13, bold: true, color: NAVY, charSpacing: 2, margin: 0 });
    s.addText(`${m.venues} venues  ·  ${m.plays} plays  ·  ${m.share} of total`, {
      x: mx + 0.3, y: y + 0.55, w: mw - 0.6, h: 0.4, fontFace: FONT, fontSize: 12.5, color: INK, margin: 0,
    });
  });
  // The gap card — Starkville
  const gy = 2.05 + 2 * 1.45;
  s.addShape("roundRect", { x: mx, y: gy, w: mw, h: 1.75, fill: { color: NAVY }, rectRadius: 0.06, line: { color: GOLD, width: 1.5 } });
  s.addText("STARKVILLE", { x: mx + 0.3, y: gy + 0.18, w: mw - 0.6, h: 0.32, fontFace: FONT, fontSize: 13, bold: true, color: GOLD, charSpacing: 2, margin: 0 });
  s.addText("0 venues  ·  0 plays  ·  your open market", {
    x: mx + 0.3, y: gy + 0.56, w: mw - 0.6, h: 0.4, fontFace: FONT, fontSize: 12.5, color: WHITE, margin: 0,
  });
  s.addText("30 screens in MSU country are running today — without FNB on them.", {
    x: mx + 0.3, y: gy + 1.0, w: mw - 0.6, h: 0.6, fontFace: FONT, fontSize: 11, italic: true, color: ICE, margin: 0,
  });
  footer(s, 3);
}

// ───────────── Slide 4 — Category mix chart (white) ─────────────
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  titleBlock(s, "Who's seeing it", "FNB shows up across everyday life, not one niche.");

  s.addChart("bar", [{
    name: "Share of plays",
    labels: DATA.categories.map(c => c.name).reverse(),
    values: DATA.categories.map(c => c.pct).reverse(),
  }], {
    x: MARGIN, y: 2.0, w: 7.1, h: 4.5,
    barDir: "bar",
    chartColors: [NAVY],
    showLegend: false,
    showTitle: false,
    showValue: true,
    dataLabelPosition: "outEnd",
    dataLabelFormatCode: '0.0"%"',
    dataLabelColor: INK,
    dataLabelFontFace: FONT,
    dataLabelFontSize: 10.5,
    catAxisLabelColor: INK,
    catAxisLabelFontFace: FONT,
    catAxisLabelFontSize: 11,
    valAxisHidden: true,
    valGridLine: { style: "none" },
    catGridLine: { style: "none" },
    valAxisMaxVal: 26,
  });

  const rx = 8.35, rw = 4.23;
  const points = [
    ["10 venue categories", "Gas stations, restaurants, salons, gyms, clinics — the full cross-section of a customer's week."],
    ["56-minute average visit", "Your message sits in front of someone while they eat lunch, get a haircut, or watch their kid's game."],
    ["Not a blur on the highway", "Indoor screens hold attention traditional boards never get."],
  ];
  points.forEach(([h, b], i) => {
    const y = 2.15 + i * 1.5;
    goldSq(s, rx, y + 0.05, 0.12);
    s.addText(h, { x: rx + 0.24, y, w: rw - 0.24, h: 0.32, fontFace: FONT, fontSize: 14, bold: true, color: NAVY, margin: 0 });
    s.addText(b, { x: rx + 0.24, y: y + 0.34, w: rw - 0.24, h: 1.0, fontFace: FONT, fontSize: 11.5, color: INK, margin: 0, lineSpacingMultiple: 1.15 });
  });
  footer(s, 4);
}

// ───────────── Slide 5 — CPM comparison (navy) ─────────────
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  titleBlock(s, "What those eyeballs cost", "You're paying a fraction of every alternative.", true);

  // Left: the hero number
  s.addShape("roundRect", { x: MARGIN, y: 2.15, w: 4.6, h: 4.1, fill: { color: NAVY_CARD }, rectRadius: 0.08, line: { color: GOLD, width: 1.5 } });
  s.addText("$0.59", { x: MARGIN, y: 2.7, w: 4.6, h: 1.3, align: "center", fontFace: FONT, fontSize: 66, bold: true, color: GOLD, margin: 0 });
  s.addText("FNB'S NETWORK CPM", { x: MARGIN, y: 4.05, w: 4.6, h: 0.35, align: "center", fontFace: FONT, fontSize: 12, color: WHITE, charSpacing: 3, bold: true, margin: 0 });
  s.addText("Cost per 1,000 impressions,\nmeasured across your whole campaign", { x: MARGIN + 0.4, y: 4.5, w: 3.8, h: 0.8, align: "center", fontFace: FONT, fontSize: 11, color: ICE, margin: 0 });

  // Right: alternatives
  const rx = 5.95, rw = 6.6;
  const alts = [
    ["Traditional billboards", "$3 – $8 CPM", "5–14× the cost"],
    ["Digital display ads", "$5 – $15 CPM", "8–25× the cost"],
    ["Social media ads", "$6 – $12 CPM", "10–20× the cost"],
  ];
  alts.forEach(([name, range, mult], i) => {
    const y = 2.15 + i * 1.12;
    s.addShape("roundRect", { x: rx, y, w: rw, h: 0.92, fill: { color: NAVY_CARD }, rectRadius: 0.06, line: { type: "none" } });
    s.addText(name, { x: rx + 0.35, y: y + 0.1, w: 3.0, h: 0.72, fontFace: FONT, fontSize: 14, bold: true, color: WHITE, margin: 0, valign: "middle" });
    s.addText(range, { x: rx + 3.35, y: y + 0.1, w: 1.5, h: 0.72, fontFace: FONT, fontSize: 13, color: ICE, margin: 0, valign: "middle" });
    s.addText(mult, { x: rx + 4.85, y: y + 0.1, w: 1.45, h: 0.72, align: "right", fontFace: FONT, fontSize: 12, bold: true, color: GOLD, margin: 0, valign: "middle" });
  });

  s.addText("Same eyeballs — in places where your ad can't be skipped, scrolled past, or blocked.", {
    x: rx, y: 5.7, w: rw, h: 0.6, fontFace: FONT, fontSize: 13, italic: true, color: ICE, margin: 0,
  });
  footer(s, 5, true);
}

// ───────────── Slide 6 — Grow With Us: the network (white) ─────────────
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  titleBlock(s, "Grow with us", "The network keeps growing. FNB should grow with it.");

  const stats = [
    [DATA.network.total_screens, "screens across North Mississippi"],
    [DATA.network.monthly_impressions, "impressions every month, network-wide"],
    [`2 of ${DATA.network.markets}`, "markets where FNB is on screen today"],
  ];
  stats.forEach(([n, l], i) => {
    const x = MARGIN + i * 4.0;
    s.addText(n, { x, y: 1.95, w: 3.7, h: 0.65, fontFace: FONT, fontSize: 36, bold: true, color: NAVY, margin: 0 });
    s.addText(l, { x, y: 2.6, w: 3.5, h: 0.55, fontFace: FONT, fontSize: 11.5, color: MUTED, margin: 0 });
  });

  const cw = 2.25, gap = 0.16, x0 = MARGIN, y0 = 3.55, ch = 2.5;
  DATA.markets_all.forEach((m, i) => {
    const x = x0 + i * (cw + gap);
    const open = m.status === "OPEN FOR FNB";
    const active = m.status === "FNB ACTIVE";
    const fill = open ? { color: NAVY } : active ? { color: LIGHT } : { color: WHITE };
    const line = open ? { color: GOLD, width: 1.5 } : { color: "E3E5EC", width: 1 };
    s.addShape("roundRect", { x, y: y0, w: cw, h: ch, fill, rectRadius: 0.06, line });
    s.addText(m.name, { x: x + 0.22, y: y0 + 0.25, w: cw - 0.44, h: 0.35, fontFace: FONT, fontSize: 15, bold: true, color: open ? WHITE : NAVY, margin: 0 });
    s.addText(String(m.screens), { x: x + 0.22, y: y0 + 0.7, w: cw - 0.44, h: 0.75, fontFace: FONT, fontSize: 40, bold: true, color: open ? GOLD : NAVY, margin: 0 });
    s.addText("SCREENS", { x: x + 0.22, y: y0 + 1.45, w: cw - 0.44, h: 0.28, fontFace: FONT, fontSize: 9, charSpacing: 2, color: open ? ICE : MUTED, margin: 0 });
    s.addText(m.status, {
      x: x + 0.22, y: y0 + 1.9, w: cw - 0.44, h: 0.3, fontFace: FONT, fontSize: 10.5, bold: true,
      color: open ? GOLD : active ? GOLD_DARK : MUTED, charSpacing: 1, margin: 0,
    });
  });

  s.addText("Columbus and West Point are coming online now — partners who grow with the network get first position as each market opens.",
    { x: MARGIN, y: 6.35, w: W - 2 * MARGIN, h: 0.5, fontFace: FONT, fontSize: 11.5, italic: true, color: MUTED, margin: 0 });
  footer(s, 6);
}

// ───────────── Slide 7 — The Starkville gap (white) ─────────────
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  titleBlock(s, "The opening", "Starkville is the piece you're missing.");

  s.addText("0", { x: MARGIN, y: 2.3, w: 3.4, h: 2.6, fontFace: FONT, fontSize: 190, bold: true, color: GOLD, margin: 0, align: "center" });
  s.addText("FNB VENUES IN STARKVILLE TODAY", {
    x: MARGIN, y: 5.15, w: 3.4, h: 0.6, align: "center", fontFace: FONT, fontSize: 11.5, bold: true, color: NAVY, charSpacing: 2, margin: 0,
  });

  const rx = 4.9, rw = 7.7;
  const pts = [
    ["30 screens in MSU country", "Mississippi State students, staff, and families across the Golden Triangle — Cotton District to The Junction."],
    ["The banking shelf is open", "No bank owns this market on our screens yet. The first one in gets the mindshare."],
    ["Football season is 5 weeks out", "Bulldog gameday traffic floods every venue on the network from September through bowl season."],
    ["It completes the map", "Oxford, Tupelo, and Starkville — consistent FNB presence across all three of North Mississippi's key population centers."],
  ];
  pts.forEach(([h, b], i) => {
    const y = 2.15 + i * 1.12;
    goldSq(s, rx, y + 0.05, 0.12);
    s.addText(h, { x: rx + 0.26, y, w: rw - 0.26, h: 0.32, fontFace: FONT, fontSize: 14.5, bold: true, color: NAVY, margin: 0 });
    s.addText(b, { x: rx + 0.26, y: y + 0.33, w: rw - 0.26, h: 0.7, fontFace: FONT, fontSize: 11.5, color: INK, margin: 0, lineSpacingMultiple: 1.12 });
  });
  footer(s, 7);
}

// ───────────── Slide 8 — Market sponsorships (white, 3 cards) ─────────────
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  titleBlock(s, "Market sponsorships", "Own a market when foot traffic peaks.");

  const cw = 3.85, gap = 0.21, y0 = 2.1, ch = 3.9;
  DATA.sponsorships.forEach((p, i) => {
    const x = MARGIN + i * (cw + gap);
    const feat = !!p.featured;
    s.addShape("roundRect", {
      x, y: y0, w: cw, h: ch,
      fill: { color: feat ? NAVY : LIGHT }, rectRadius: 0.08,
      line: feat ? { color: GOLD, width: 1.5 } : { type: "none" },
    });
    if (feat) {
      s.addText("IN THE PLAN", { x: x + 0.3, y: y0 + 0.22, w: cw - 0.6, h: 0.28, fontFace: FONT, fontSize: 9.5, bold: true, color: GOLD, charSpacing: 3, margin: 0 });
    }
    s.addText(p.name, {
      x: x + 0.3, y: y0 + 0.52, w: cw - 0.6, h: 0.75, fontFace: FONT, fontSize: 17, bold: true,
      color: feat ? WHITE : NAVY, margin: 0,
    });
    s.addText(p.screens, { x: x + 0.3, y: y0 + 1.28, w: cw - 0.6, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, color: feat ? GOLD : GOLD_DARK, margin: 0 });
    s.addText(p.detail, {
      x: x + 0.3, y: y0 + 1.66, w: cw - 0.6, h: 1.15, fontFace: FONT, fontSize: 11.5,
      color: feat ? ICE : INK, margin: 0, lineSpacingMultiple: 1.15,
    });
    s.addText(p.total, { x: x + 0.3, y: y0 + 2.85, w: cw - 0.6, h: 0.6, fontFace: FONT, fontSize: 30, bold: true, color: feat ? GOLD : NAVY, margin: 0 });
    s.addText(p.price, { x: x + 0.3, y: y0 + 3.42, w: cw - 0.6, h: 0.3, fontFace: FONT, fontSize: 10.5, color: feat ? ICE : MUTED, margin: 0 });
  });

  s.addText("Seasonal saturation buys the whole market's attention for the stretch that matters — then hands the momentum back to your year-round campaign.",
    { x: MARGIN, y: 6.35, w: W - 2 * MARGIN, h: 0.5, fontFace: FONT, fontSize: 11.5, italic: true, color: MUTED, margin: 0 });
  footer(s, 8);
}

// ───────────── Slide 9 — The $10K plan (navy, money slide) ─────────────
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  titleBlock(s, "The recommendation", "The $10K Grow With Us Plan.", true);

  // Left: line items
  const lw = 6.7;
  DATA.plan.items.forEach((it, i) => {
    const y = 2.1 + i * 1.62;
    s.addShape("roundRect", { x: MARGIN, y, w: lw, h: 1.42, fill: { color: NAVY_CARD }, rectRadius: 0.06, line: { type: "none" } });
    s.addText(it.name, { x: MARGIN + 0.32, y: y + 0.18, w: lw - 2.0, h: 0.35, fontFace: FONT, fontSize: 15, bold: true, color: WHITE, margin: 0 });
    s.addText(it.detail, { x: MARGIN + 0.32, y: y + 0.56, w: lw - 2.0, h: 0.75, fontFace: FONT, fontSize: 11.5, color: ICE, margin: 0, lineSpacingMultiple: 1.15 });
    s.addText(it.total, { x: MARGIN + lw - 1.75, y: y + 0.18, w: 1.45, h: 1.06, align: "right", fontFace: FONT, fontSize: 22, bold: true, color: GOLD, margin: 0, valign: "top" });
  });

  const ty = 2.1 + 2 * 1.62 + 0.1;
  s.addShape("line", { x: MARGIN, y: ty, w: lw, h: 0, line: { color: GOLD, width: 1.5 } });
  s.addText("TOTAL — FIRST 12 MONTHS", { x: MARGIN + 0.05, y: ty + 0.22, w: 4.0, h: 0.4, fontFace: FONT, fontSize: 12.5, bold: true, color: WHITE, charSpacing: 2, margin: 0, valign: "middle" });
  s.addText(DATA.plan.total, { x: MARGIN + lw - 2.6, y: ty + 0.08, w: 2.55, h: 0.75, align: "right", fontFace: FONT, fontSize: 40, bold: true, color: GOLD, margin: 0 });

  // Right: what it gets
  const rx = 8.05, rw = 4.55;
  s.addText("WHAT IT ADDS", { x: rx, y: 2.1, w: rw, h: 0.32, fontFace: FONT, fontSize: 11, bold: true, color: GOLD, charSpacing: 3, margin: 0 });
  DATA.plan.gets.forEach((g, i) => {
    const y = 2.55 + i * 0.92;
    goldSq(s, rx, y + 0.04, 0.11);
    s.addText(g, { x: rx + 0.24, y, w: rw - 0.24, h: 0.85, fontFace: FONT, fontSize: 12, color: WHITE, margin: 0, lineSpacingMultiple: 1.12, valign: "top" });
  });

  s.addText("Proposed structure — final package and terms confirmed with your MCTV rep.", {
    x: MARGIN, y: 6.55, w: W - 2 * MARGIN, h: 0.35, fontFace: FONT, fontSize: 10.5, italic: true, color: ICE, margin: 0,
  });
  footer(s, 9, true);
}

// ───────────── Slide 10 — Why now (white) ─────────────
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  titleBlock(s, "Why now", "Three reasons this window matters.");

  const cards = [
    ["01", "The season is coming", "Football and back-to-school traffic hit in five weeks. Screens booked now are on the wall when the crowds show up — not after."],
    ["02", "Your rate gets protected", "Commit now and lock today's pricing for the full term. As the network grows, new advertisers pay the new rates. You won't."],
    ["03", "Momentum compounds", "Six months of steady presence built real recognition. Expansion multiplies what you already paid to build — starting over later doesn't."],
  ];
  const cw = 3.85, gap = 0.21, y0 = 2.15, ch = 3.6;
  cards.forEach(([n, h, b], i) => {
    const x = MARGIN + i * (cw + gap);
    s.addShape("roundRect", { x, y: y0, w: cw, h: ch, fill: { color: LIGHT }, rectRadius: 0.08, line: { type: "none" } });
    s.addText(n, { x: x + 0.32, y: y0 + 0.3, w: cw - 0.64, h: 0.7, fontFace: FONT, fontSize: 40, bold: true, color: GOLD, margin: 0 });
    s.addText(h, { x: x + 0.32, y: y0 + 1.15, w: cw - 0.64, h: 0.4, fontFace: FONT, fontSize: 16, bold: true, color: NAVY, margin: 0 });
    s.addText(b, { x: x + 0.32, y: y0 + 1.6, w: cw - 0.64, h: 1.8, fontFace: FONT, fontSize: 12, color: INK, margin: 0, lineSpacingMultiple: 1.25 });
  });

  s.addText("Sep 1 — Bulldog and Rebel football season  ·  Nov 15 — holiday saturation begins  ·  Jan 1 — a full year of three-market coverage underway",
    { x: MARGIN, y: 6.3, w: W - 2 * MARGIN, h: 0.5, fontFace: FONT, fontSize: 11.5, color: MUTED, align: "center", margin: 0 });
  footer(s, 10);
}

// ───────────── Slide 11 — Next steps + team (navy close) ─────────────
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  titleBlock(s, "Next steps", "Fifteen minutes is all it takes.", true);

  s.addText("We'll walk through the plan, answer questions, and get the paperwork moving — your ads keep playing the whole time.", {
    x: MARGIN, y: 1.85, w: 11.5, h: 0.45, fontFace: FONT, fontSize: 13.5, color: ICE, margin: 0,
  });

  const cw = 3.85, gap = 0.21, y0 = 2.65, ch = 3.35;
  DATA.team.forEach((t, i) => {
    const x = MARGIN + i * (cw + gap);
    s.addShape("roundRect", { x, y: y0, w: cw, h: ch, fill: { color: NAVY_CARD }, rectRadius: 0.08, line: { type: "none" } });
    const ps = 1.35;
    s.addImage({ path: path.join(ASSETS, "team", t.photo), x: x + (cw - ps) / 2, y: y0 + 0.35, w: ps, h: ps, rounding: true });
    s.addText(t.name, { x: x + 0.2, y: y0 + 1.85, w: cw - 0.4, h: 0.34, align: "center", fontFace: FONT, fontSize: 15, bold: true, color: WHITE, margin: 0 });
    s.addText(t.title.toUpperCase(), { x: x + 0.2, y: y0 + 2.2, w: cw - 0.4, h: 0.28, align: "center", fontFace: FONT, fontSize: 9.5, color: GOLD, charSpacing: 2, margin: 0 });
    s.addText(`${t.phone}\n${t.email}`, { x: x + 0.2, y: y0 + 2.55, w: cw - 0.4, h: 0.62, align: "center", fontFace: FONT, fontSize: 11, color: ICE, margin: 0, lineSpacingMultiple: 1.25 });
  });

  const lw2 = 1.9;
  s.addImage({ path: logoWhite, x: (W - lw2) / 2, y: 6.45, w: lw2, h: lw2 / LOGO_AR });
}

pres.writeFile({ fileName: OUT }).then(() => console.log("WROTE", OUT));
