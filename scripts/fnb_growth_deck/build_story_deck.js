// FNB × MCTV — "Grow With Us" story deck, v4
// Restructure per rep feedback: results/data first (slides 2-6), pitch second
// (partners → ticker → Grove → ask). Starkville expansion cut — the play is
// Oxford + Tupelo full-network + Market Ticker. 20-screen origin story added.
// node build_deck2.js  → FNB_GrowWithUs_Story_Deck.pptx

const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const S = __dirname;
const ASSETS = path.join(__dirname, "..", "..", "assets");
const OUT = path.join(__dirname, "..", "..", "output", "decks", "FNB_GrowWithUs_Story_Deck.pptx");
fs.mkdirSync(path.dirname(OUT), { recursive: true });

const NAVY = "12162E";
const NAVY2 = "1B1F3B";
const CARD = "222847";
const CARD2 = "1A1F3D";
const GOLD = "C5A55A";
const GOLDB = "E3C57B";
const WHITE = "FFFFFF";
const ICE = "C9CDE0";
const MUTE = "8A90AD";
const FNBNAVY = "0D2C54";
const GROVE = "A6192E";
const GROVEP = "FF8FA0";
const FONT = "Arial";
const W = 13.333, H = 7.5, M = 0.75;
const AP = "’";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "MCTV Elite Advertising";
pres.title = "FNB × MCTV — Grow With Us";

const logoWhite = path.join(ASSETS, "branding/mctv_logo_white.png");
const LOGO_AR = 934 / 283;
const FNB_MARK = path.join(S, "fnb_mark.png");    // 190x210 shield
const GROVE_MARK = path.join(S, "grove_mark.png"); // 200x200 circle
const FNB_AR = 190 / 210;

const gsq = (s, x, y, sz) => s.addShape("rect", { x, y, w: sz || 0.14, h: sz || 0.14, fill: { color: GOLD } });
const bullet = () => ({ characterCode: "25AA", indent: 14 });

function header(s, kicker, title, opts = {}) {
  gsq(s, M, 0.62, 0.14);
  s.addText(kicker.toUpperCase(), { x: M + 0.26, y: 0.47, w: 9.5, h: 0.42, fontFace: FONT, fontSize: 12,
    color: GOLD, charSpacing: 3, bold: true, margin: 0, valign: "middle" });
  s.addText(title, { x: M, y: 0.92, w: W - 2 * M, h: 0.85, fontFace: FONT, fontSize: opts.size || 32,
    bold: true, color: WHITE, margin: 0, valign: "top" });
  s.addImage({ path: logoWhite, x: W - M - 1.15, y: 0.55, w: 1.15, h: 1.15 / LOGO_AR });
}

function footer(s, n) {
  s.addText(`MCTV ELITE ADVERTISING  ·  FNB GROWTH STORY  ·  ${n}`, {
    x: M, y: 7.1, w: W - 2 * M, h: 0.28, align: "right", fontFace: FONT, fontSize: 8.5,
    color: MUTE, charSpacing: 2, margin: 0 });
}

const darkSlide = () => { const s = pres.addSlide(); s.background = { color: NAVY }; return s; };

// ── 1 · COVER ────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { path: path.join(S, "art_cover.png") };
  s.addImage({ path: logoWhite, x: M, y: 0.72, w: 2.3, h: 2.3 / LOGO_AR });
  gsq(s, M, 2.62, 0.2);
  s.addText("GROW", { x: M, y: 2.86, w: 6.3, h: 1.05, fontFace: FONT, fontSize: 76, bold: true, color: WHITE, margin: 0 });
  s.addText("WITH US.", { x: M, y: 3.86, w: 6.3, h: 1.05, fontFace: FONT, fontSize: 76, bold: true, color: GOLDB, margin: 0 });
  s.addText(`The FNB Oxford Bank story on North Mississippi${AP}s screens —\nsix months in, and just getting started.`, {
    x: M, y: 5.1, w: 6.1, h: 0.9, fontFace: FONT, fontSize: 15, color: ICE, margin: 0, lineSpacingMultiple: 1.3 });
  s.addText("PREPARED FOR OUR PARTNERS AT FNB OXFORD BANK · JULY 2026", {
    x: M, y: 6.55, w: 7.1, h: 0.35, fontFace: FONT, fontSize: 10, color: GOLD, charSpacing: 1.5, bold: true, margin: 0 });
}

// ── 2 · THE RESULTS ──────────────────────────────────────────────────
{
  const s = darkSlide();
  header(s, "Your results · Jan 31 – Jul 20, 2026", `You trusted us with your name. Here${AP}s what happened.`);

  s.addText("392,395", { x: M, y: 2.1, w: 8.2, h: 1.75, fontFace: FONT, fontSize: 120, bold: true, color: GOLDB, margin: 0 });
  s.addText("TIMES YOUR NAME LIT UP A SCREEN IN NORTH MISSISSIPPI", {
    x: M + 0.05, y: 4.12, w: 7.6, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: WHITE, charSpacing: 3, margin: 0 });
  s.addText("Source: NTV360 network analytics", {
    x: M + 0.05, y: 4.57, w: 7.0, h: 0.32, fontFace: FONT, fontSize: 11, color: MUTE, margin: 0 });

  s.addShape("roundRect", { x: 9.0, y: 2.35, w: 3.58, h: 1.95, fill: { color: CARD2 }, rectRadius: 0.08, line: { color: GOLD, width: 1.25 } });
  s.addText("2,294", { x: 9.3, y: 2.62, w: 3.0, h: 0.85, fontFace: FONT, fontSize: 48, bold: true, color: WHITE, margin: 0 });
  s.addText("PLAYS A DAY, RAIN OR SHINE", { x: 9.3, y: 3.55, w: 3.0, h: 0.5, fontFace: FONT, fontSize: 10.5, bold: true, color: GOLDB, charSpacing: 2, margin: 0 });

  const stats = [
    ["65", "venues carrying FNB"],
    ["3,788 hrs", "of screen time"],
    ["1.4M+", "impressions monthly"],
    ["56 min", "average dwell time"],
  ];
  stats.forEach(([n, l], i) => {
    const x = M + i * 3.02;
    s.addShape("roundRect", { x, y: 5.15, w: 2.77, h: 1.5, fill: { color: CARD }, rectRadius: 0.07, line: { type: "none" } });
    s.addText(n, { x: x + 0.25, y: 5.35, w: 2.3, h: 0.6, fontFace: FONT, fontSize: 30, bold: true, color: WHITE, margin: 0 });
    s.addText(l.toUpperCase(), { x: x + 0.25, y: 6.0, w: 2.3, h: 0.5, fontFace: FONT, fontSize: 9.5, color: MUTE, charSpacing: 1.5, margin: 0 });
  });
  footer(s, 2);
}

// ── 3 · MOMENTS ──────────────────────────────────────────────────────
{
  const s = darkSlide();
  header(s, "Where they saw you", "Your name became part of daily life.");
  s.addText("Not a blur on the highway. Not an ad to skip. FNB showed up in the middle of the moments that make up a week in Mississippi.", {
    x: M, y: 1.8, w: 11.5, h: 0.6, fontFace: FONT, fontSize: 14, color: ICE, margin: 0, lineSpacingMultiple: 1.25 });
  const iw = W - 2 * M, ih = iw * (640 / 1920);
  s.addImage({ path: path.join(S, "art_moments.png"), x: M, y: 2.62, w: iw, h: ih });
  s.addText("…and 61 more venues just like these, every day, all day.", {
    x: M, y: 6.72, w: 11.83, h: 0.35, align: "center", fontFace: FONT, fontSize: 12.5, italic: true, color: MUTE, margin: 0 });
  footer(s, 3);
}

// ── 4 · PROOF + the 20-screen story ──────────────────────────────────
{
  const s = darkSlide();
  header(s, "The receipts", "Every venue, measured. These led the pack.");

  const venues = [
    ["Oxford Park Commission", "Community", "49,379", "$0.72"],
    ["Rebel Body Fitness", "Fitness", "20,780", "$2.33"],
    ["Amara Salon & Aesthetics", "Salon", "20,170", "$2.80"],
    ["Texaco Lamar Express", "General", "17,439", "$1.41"],
    ["Marathon South Lamar", "General", "14,647", "$1.18"],
    ["Rainbow Cleaners", "General", "14,192", "$6.27"],
    ["4 Corner's Chevron", "Rest & Bar", "12,121", "$0.98"],
  ];
  const rows = [[
    { text: "VENUE", options: { bold: true, color: GOLDB, fill: { color: NAVY2 } } },
    { text: "CATEGORY", options: { bold: true, color: GOLDB, fill: { color: NAVY2 } } },
    { text: "PLAYS", options: { bold: true, color: GOLDB, fill: { color: NAVY2 }, align: "right" } },
    { text: "CPM", options: { bold: true, color: GOLDB, fill: { color: NAVY2 }, align: "right" } },
  ]];
  venues.forEach((v, i) => {
    const fill = { color: i === 0 ? "2E3560" : i % 2 ? CARD2 : CARD };
    rows.push([
      { text: v[0], options: { fill, color: WHITE, bold: i === 0 } },
      { text: v[1], options: { fill, color: MUTE } },
      { text: v[2], options: { fill, color: WHITE, bold: i === 0, align: "right" } },
      { text: v[3], options: { fill, color: ICE, align: "right" } },
    ]);
  });
  s.addTable(rows, { x: M, y: 2.05, w: 6.9, colW: [3.15, 1.45, 1.25, 1.05], fontFace: FONT, fontSize: 11,
    rowH: 0.42, valign: "middle", border: { type: "solid", color: "2A305A", pt: 0.5 } });
  s.addText([
    { text: "Oxford Park Commission outplayed the next two venues combined — hometown families, week after week.", options: { breakLine: true, italic: true, color: MUTE } },
    { text: "The full 65-venue table is in your traction report.", options: { italic: true, color: MUTE } },
  ], { x: M, y: 5.72, w: 6.9, h: 0.85, fontFace: FONT, fontSize: 11.5, margin: 0, lineSpacingMultiple: 1.25 });

  const mx = 8.05, mw = 4.53;
  const mk = [["OXFORD", "41 venues · 339,061 plays · 86.4% of FNB plays"], ["TUPELO", "24 venues · 53,334 plays · 13.6% of FNB plays"]];
  mk.forEach(([n, d], i) => {
    const y = 2.05 + i * 1.45;
    s.addShape("roundRect", { x: mx, y, w: mw, h: 1.18, fill: { color: CARD }, rectRadius: 0.07, line: { type: "none" } });
    s.addText(n, { x: mx + 0.3, y: y + 0.15, w: mw - 0.6, h: 0.32, fontFace: FONT, fontSize: 13, bold: true, color: GOLDB, charSpacing: 2, margin: 0 });
    s.addText(d, { x: mx + 0.3, y: y + 0.53, w: mw - 0.6, h: 0.5, fontFace: FONT, fontSize: 11.5, color: WHITE, margin: 0, lineSpacingMultiple: 1.1 });
  });
  // the 20-screen origin story
  const gy = 2.05 + 2 * 1.45;
  s.addShape("roundRect", { x: mx, y: gy, w: mw, h: 1.8, fill: { color: FNBNAVY }, rectRadius: 0.07, line: { color: GOLD, width: 1.5 } });
  s.addText("3× WHAT YOU SIGNED FOR", { x: mx + 0.3, y: gy + 0.2, w: mw - 0.6, h: 0.32, fontFace: FONT, fontSize: 13, bold: true, color: GOLDB, charSpacing: 2, margin: 0 });
  s.addText("FNB joined MCTV as a 20-screen partner. Today your ad plays across 65 venues.", {
    x: mx + 0.3, y: gy + 0.58, w: mw - 0.6, h: 0.6, fontFace: FONT, fontSize: 12, color: WHITE, margin: 0, lineSpacingMultiple: 1.15 });
  s.addText("Partners grow with us. That${AP}s the deal.".replace("${AP}", AP), {
    x: mx + 0.3, y: gy + 1.28, w: mw - 0.6, h: 0.4, fontFace: FONT, fontSize: 11, italic: true, color: ICE, margin: 0 });
  footer(s, 4);
}

// ── 5 · $0.59 ────────────────────────────────────────────────────────
{
  const s = darkSlide();
  header(s, "Your cost of attention", "All of that, for pennies per thousand people.");

  s.addShape("roundRect", { x: M, y: 2.15, w: 4.6, h: 4.1, fill: { color: CARD2 }, rectRadius: 0.08, line: { color: GOLD, width: 1.5 } });
  s.addText("$0.59", { x: M, y: 2.95, w: 4.6, h: 1.3, align: "center", fontFace: FONT, fontSize: 66, bold: true, color: GOLDB, margin: 0 });
  s.addText(`FNB${AP}S NETWORK CPM`, { x: M, y: 4.3, w: 4.6, h: 0.35, align: "center", fontFace: FONT, fontSize: 12, color: WHITE, charSpacing: 3, bold: true, margin: 0 });
  s.addText("Cost per 1,000 impressions,\nmeasured across the full campaign", { x: M + 0.4, y: 4.78, w: 3.8, h: 0.8, align: "center", fontFace: FONT, fontSize: 11, color: ICE, margin: 0 });

  const rx = 5.95, rw = 6.6;
  const alts = [
    ["Traditional billboards", "$3–$8 CPM", "5–14× more"],
    ["Digital display ads", "$5–$15 CPM", "8–25× more"],
    ["Social media ads", "$6–$12 CPM", "10–20× more"],
  ];
  alts.forEach(([n, r, m2], i) => {
    const y = 2.15 + i * 1.12;
    s.addShape("roundRect", { x: rx, y, w: rw, h: 0.92, fill: { color: CARD }, rectRadius: 0.06, line: { type: "none" } });
    s.addText(n, { x: rx + 0.35, y: y + 0.1, w: 3.0, h: 0.72, fontFace: FONT, fontSize: 14, bold: true, color: WHITE, margin: 0, valign: "middle" });
    s.addText(r, { x: rx + 3.35, y: y + 0.1, w: 1.5, h: 0.72, fontFace: FONT, fontSize: 13, color: ICE, margin: 0, valign: "middle" });
    s.addText(m2, { x: rx + 4.85, y: y + 0.1, w: 1.45, h: 0.72, align: "right", fontFace: FONT, fontSize: 12, bold: true, color: GOLDB, margin: 0, valign: "middle" });
  });
  s.addText(`Same eyeballs — in rooms where ads can${AP}t be skipped or blocked.`, {
    x: rx, y: 5.7, w: rw, h: 0.4, fontFace: FONT, fontSize: 13, italic: true, color: ICE, margin: 0 });
  footer(s, 5);
}

// ── 6 · OWN BOTH TOWNS — the map ─────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { path: path.join(S, "art_map.png") };
  gsq(s, M, 0.62, 0.14);
  s.addText("THE NEXT STEP", { x: M + 0.26, y: 0.47, w: 9, h: 0.42, fontFace: FONT, fontSize: 12, color: GOLD, charSpacing: 3, bold: true, margin: 0, valign: "middle" });
  s.addText("Your towns. Our screens.\nOwn them end to end.", {
    x: M, y: 0.95, w: 7.5, h: 1.5, fontFace: FONT, fontSize: 32, bold: true, color: WHITE, margin: 0 });
  s.addImage({ path: logoWhite, x: W - M - 1.15, y: 0.55, w: 1.15, h: 1.15 / LOGO_AR });
  s.addText("You started with 20 screens.\nYou outgrew them. The full network\nis 100 — every venue we run\nin Oxford and Tupelo.", {
    x: M, y: 2.75, w: 3.9, h: 1.7, fontFace: FONT, fontSize: 13.5, bold: true, color: GOLDB, margin: 0, lineSpacingMultiple: 1.3 });
  footer(s, 6);
}

// ── 7 · PARTNERS — sets up the sponsorship pitch ─────────────────────
{
  const s = darkSlide();
  header(s, "Before the pitch", "Two hometown names. One team.");

  s.addText("What comes next is a sponsorship — and who you sponsor matters as much as where. These are the names on it.", {
    x: M, y: 1.78, w: 10.2, h: 0.62, fontFace: FONT, fontSize: 14, color: ICE, margin: 0, lineSpacingMultiple: 1.25 });

  s.addShape("roundRect", { x: M, y: 2.6, w: 5.85, h: 3.55, fill: { color: FNBNAVY }, rectRadius: 0.1, line: { color: GOLD, width: 1.5 } });
  s.addImage({ path: FNB_MARK, x: M + 4.55, y: 2.9, w: 0.95 * FNB_AR, h: 0.95 });
  s.addText("FOUNDING PARTNER", { x: M + 0.4, y: 2.95, w: 4.0, h: 0.3, fontFace: FONT, fontSize: 10, bold: true, color: GOLDB, charSpacing: 4, margin: 0 });
  s.addText("FNB OXFORD BANK", { x: M + 0.4, y: 3.3, w: 4.1, h: 0.55, fontFace: FONT, fontSize: 26, bold: true, color: WHITE, margin: 0 });
  s.addShape("rect", { x: M + 0.42, y: 3.95, w: 1.0, h: 0.07, fill: { color: GOLD } });
  s.addText(`“North Mississippi${AP}s Friendly Neighborhood Bank”`, {
    x: M + 0.4, y: 4.18, w: 5.05, h: 0.4, fontFace: FONT, fontSize: 13.5, italic: true, color: GOLDB, margin: 0 });
  s.addText([
    { text: "Serving neighbors since 1910", options: { breakLine: true, bullet: bullet(), paraSpaceAfter: 8 } },
    { text: "Headquartered on the historic Oxford Square", options: { breakLine: true, bullet: bullet(), paraSpaceAfter: 8 } },
    { text: "Six locations — Oxford, Tupelo, Water Valley", options: { bullet: bullet() } },
  ], { x: M + 0.4, y: 4.72, w: 5.05, h: 1.25, fontFace: FONT, fontSize: 12.5, color: ICE, margin: 0, lineSpacingMultiple: 1.1 });

  const gx = M + 6.1;
  s.addShape("roundRect", { x: gx, y: 2.6, w: 5.85, h: 3.55, fill: { color: CARD }, rectRadius: 0.1, line: { color: GROVE, width: 1.5 } });
  s.addText("COMMUNITY PARTNER", { x: gx + 0.4, y: 2.82, w: 4.0, h: 0.3, fontFace: FONT, fontSize: 10, bold: true, color: GROVEP, charSpacing: 4, margin: 0 });
  // Grove wordmark on white plate (dark-background display convention)
  s.addShape("roundRect", { x: gx + 0.4, y: 3.18, w: 2.75, h: 0.92, fill: { color: WHITE }, rectRadius: 0.07, line: { type: "none" } });
  s.addImage({ path: path.join(S, "grove_wordmark.png"), x: gx + 0.62, y: 3.33, w: 1.25 * (1920 / 940) * 0.55, h: 0.62 });
  s.addText("THE GROVE COLLECTIVE", { x: gx + 3.35, y: 3.18, w: 2.2, h: 0.92, fontFace: FONT, fontSize: 13, bold: true, color: WHITE, margin: 0, valign: "middle", lineSpacingMultiple: 1.15 });
  s.addText(`Ole Miss${AP}s official NIL collective`, {
    x: gx + 0.4, y: 4.18, w: 5.05, h: 0.4, fontFace: FONT, fontSize: 13.5, italic: true, color: GROVEP, margin: 0 });
  s.addText([
    { text: "Funds 150+ Ole Miss student-athletes", options: { breakLine: true, bullet: bullet(), paraSpaceAfter: 8 } },
    { text: "Across all 18 Rebel sports", options: { breakLine: true, bullet: bullet(), paraSpaceAfter: 8 } },
    { text: "Keeping championship talent in Oxford", options: { bullet: bullet() } },
  ], { x: gx + 0.4, y: 4.72, w: 5.05, h: 1.25, fontFace: FONT, fontSize: 12.5, color: ICE, margin: 0, lineSpacingMultiple: 1.1 });

  s.addText("Grove Collective mark recreated from brand reference · FNB mark is a placeholder pending their logo file.", {
    x: M, y: 6.5, w: 11.83, h: 0.35, align: "center", fontFace: FONT, fontSize: 9.5, italic: true, color: MUTE, margin: 0 });
  footer(s, 7);
}

// ── 8 · FLAGSHIP: MARKET TICKER ──────────────────────────────────────
{
  const s = darkSlide();
  header(s, "New · flagship sponsorship", "Own the markets. Literally.", { size: 30 });

  s.addShape("roundRect", { x: M - 0.06, y: 1.99, w: 7.32, h: 4.24, fill: { color: "05070F" }, rectRadius: 0.05, line: { color: GOLD, width: 1.5 } });
  s.addImage({ path: path.join(S, "frame_product.png"), x: M, y: 2.05, w: 7.2, h: 4.05 });
  s.addText("PRODUCT MOCK WITH YOUR BRANDING — FULL-MOTION DEMO READY TODAY", { x: M, y: 6.2, w: 7.2, h: 0.3, align: "center",
    fontFace: FONT, fontSize: 9.5, color: MUTE, charSpacing: 2, margin: 0 });

  const rx = 8.35, rw = 4.25;
  s.addText("THE MCTV MARKET TICKER", { x: rx, y: 2.05, w: rw, h: 0.32, fontFace: FONT, fontSize: 13, bold: true, color: GOLDB, charSpacing: 2, margin: 0 });
  s.addText("Live market updates on every screen we run — with one name on the ticker, all day: yours.", {
    x: rx, y: 2.45, w: rw, h: 0.75, fontFace: FONT, fontSize: 12.5, color: ICE, margin: 0, lineSpacingMultiple: 1.2 });
  const pts = [
    "“Presented by FNB Oxford Bank” on every update",
    "100 screens across Oxford + Tupelo",
    "Exclusive — no other bank, ever",
    "Grove Collective give-back built in",
  ];
  pts.forEach((p, i) => {
    const y = 3.4 + i * 0.62;
    gsq(s, rx, y + 0.05, 0.11);
    s.addText(p, { x: rx + 0.24, y, w: rw - 0.24, h: 0.55, fontFace: FONT, fontSize: 12, color: WHITE, margin: 0, valign: "top", lineSpacingMultiple: 1.1 });
  });
  s.addShape("line", { x: rx, y: 5.95, w: rw, h: 0, line: { color: GOLD, width: 1.5 } });
  s.addText("$3,000/mo", { x: rx, y: 6.1, w: 2.6, h: 0.6, fontFace: FONT, fontSize: 32, bold: true, color: GOLDB, margin: 0 });
  s.addText("MARKET SPONSOR\nEXCLUSIVE", { x: rx + 2.65, y: 6.14, w: 1.6, h: 0.55, fontFace: FONT, fontSize: 9.5, bold: true, color: MUTE, charSpacing: 1.5, margin: 0 });
  footer(s, 8);
}

// ── 9 · GROVE TIE-IN ─────────────────────────────────────────────────
{
  const s = darkSlide();
  header(s, "The Grove Collective tie-in", "Sponsorship that stays home.");

  s.addText("A share of every Market Sponsor dollar goes to The Grove Collective — the official NIL program keeping Ole Miss athletes in Oxford. When FNB sponsors the ticker, the hometown bank funds hometown champions. That${AP}s a story no billboard can tell.".replace("${AP}", AP), {
    x: M, y: 1.85, w: 11.8, h: 0.95, fontFace: FONT, fontSize: 14.5, color: ICE, margin: 0, lineSpacingMultiple: 1.3 });

  const cards = [
    ["150+", "OLE MISS ATHLETES FUNDED", GROVEP],
    ["18", "REBEL SPORTS SUPPORTED", GROVEP],
    ["1", "BANK ON THE TICKER: FNB", GOLDB],
  ];
  cards.forEach(([n, l, c], i) => {
    const x = M + i * 4.04;
    s.addShape("roundRect", { x, y: 3.15, w: 3.75, h: 2.15, fill: { color: CARD2 }, rectRadius: 0.08, line: { type: "none" } });
    s.addText(n, { x: x + 0.3, y: 3.4, w: 3.15, h: 0.95, fontFace: FONT, fontSize: 54, bold: true, color: c, margin: 0 });
    s.addText(l, { x: x + 0.3, y: 4.5, w: 3.15, h: 0.55, fontFace: FONT, fontSize: 11, bold: true, color: WHITE, charSpacing: 1.5, margin: 0 });
  });

  s.addShape("roundRect", { x: M, y: 5.75, w: 11.83, h: 0.95, fill: { color: "2A1220" }, rectRadius: 0.08, line: { color: GROVE, width: 1 } });
  s.addImage({ path: GROVE_MARK, x: M + 0.3, y: 5.92, w: 0.6, h: 0.6 });
  s.addText([
    { text: "On screen, in every rotation:  ", options: { bold: true, color: WHITE } },
    { text: "“FNB Oxford Bank — proud supporter of The Grove Collective and Ole Miss athletics.”", options: { italic: true, color: GROVEP } },
  ], { x: M + 1.1, y: 5.75, w: 10.4, h: 0.95, fontFace: FONT, fontSize: 13.5, margin: 0, valign: "middle" });
  footer(s, 9);
}

// ── 10 · THE ASK — full network + ticker ─────────────────────────────
{
  const s = darkSlide();
  header(s, "The ask", "Own Oxford and Tupelo. All of it.");

  const cw = 5.765, x2 = M + cw + 0.3;

  // flagship: market sponsor
  s.addShape("roundRect", { x: M, y: 2.0, w: cw, h: 4.35, fill: { color: FNBNAVY }, rectRadius: 0.1, line: { color: GOLD, width: 2 } });
  s.addImage({ path: FNB_MARK, x: M + cw - 1.1, y: 2.25, w: 0.72 * FNB_AR, h: 0.72 });
  s.addText("FLAGSHIP", { x: M + 0.4, y: 2.28, w: 3.0, h: 0.3, fontFace: FONT, fontSize: 10, bold: true, color: GOLDB, charSpacing: 4, margin: 0 });
  s.addText("Market Sponsor", { x: M + 0.4, y: 2.6, w: cw - 0.8, h: 0.55, fontFace: FONT, fontSize: 26, bold: true, color: WHITE, margin: 0 });
  s.addText([
    { text: "The Market Ticker, presented by FNB — exclusive", options: { breakLine: true, bullet: bullet(), paraSpaceAfter: 8 } },
    { text: "100 screens · Oxford + Tupelo · all day, every day", options: { breakLine: true, bullet: bullet(), paraSpaceAfter: 8 } },
    { text: "Grove Collective give-back on every dollar", options: { breakLine: true, bullet: bullet(), paraSpaceAfter: 8 } },
    { text: "Category lockout — no other bank on the ticker", options: { bullet: bullet() } },
  ], { x: M + 0.4, y: 3.28, w: cw - 0.8, h: 1.75, fontFace: FONT, fontSize: 12, color: ICE, margin: 0, lineSpacingMultiple: 1.1 });
  s.addText("$3,000/mo", { x: M + 0.4, y: 5.18, w: 3.4, h: 0.7, fontFace: FONT, fontSize: 38, bold: true, color: GOLDB, margin: 0 });
  s.addText("mctvofms.com/market-sponsor", { x: M + 0.4, y: 5.92, w: cw - 0.8, h: 0.3, fontFace: FONT, fontSize: 11, color: ICE, margin: 0 });

  // full network partner
  s.addShape("roundRect", { x: x2, y: 2.0, w: cw, h: 4.35, fill: { color: CARD2 }, rectRadius: 0.1, line: { color: "3A4271", width: 1.25 } });
  s.addText("UPGRADE", { x: x2 + 0.4, y: 2.28, w: 3.0, h: 0.3, fontFace: FONT, fontSize: 10, bold: true, color: ICE, charSpacing: 4, margin: 0 });
  s.addText("Full Network Partner", { x: x2 + 0.4, y: 2.6, w: cw - 0.8, h: 0.55, fontFace: FONT, fontSize: 26, bold: true, color: WHITE, margin: 0 });
  s.addText([
    { text: "Every screen we run in Oxford and Tupelo — 100 total", options: { breakLine: true, bullet: bullet(), paraSpaceAfter: 8 } },
    { text: "Up from the 20-screen package you started on", options: { breakLine: true, bullet: bullet(), paraSpaceAfter: 8 } },
    { text: "1.9M+ monthly network impressions behind your name", options: { breakLine: true, bullet: bullet(), paraSpaceAfter: 8 } },
    { text: "Rate locked for the full term — quarterly creative refresh included", options: { bullet: bullet() } },
  ], { x: x2 + 0.4, y: 3.28, w: cw - 0.8, h: 1.75, fontFace: FONT, fontSize: 12, color: ICE, margin: 0, lineSpacingMultiple: 1.1 });
  s.addText("$1,300/mo", { x: x2 + 0.4, y: 5.18, w: 3.4, h: 0.7, fontFace: FONT, fontSize: 38, bold: true, color: WHITE, margin: 0 });
  s.addText("Standard full-network rate, held at today's pricing".replace("today's", `today${AP}s`), { x: x2 + 0.4, y: 5.92, w: cw - 0.8, h: 0.3, fontFace: FONT, fontSize: 11, color: ICE, margin: 0 });

  s.addText("Do both, and FNB owns both towns — every screen, every day, and the only bank on the ticker. Final terms with your MCTV rep.", {
    x: M, y: 6.6, w: 11.83, h: 0.4, align: "center", fontFace: FONT, fontSize: 12, italic: true, color: GOLDB, margin: 0 });
  footer(s, 10);
}

// ── 11 · WHY NOW ─────────────────────────────────────────────────────
{
  const s = darkSlide();
  header(s, "Why now", "Five weeks to kickoff.");
  const cards = [
    ["01", "The season is coming", "Football and back-to-school traffic hit in five weeks. Sponsors locked in now are on the wall when the crowds arrive — not after."],
    ["02", "Exclusive means one", "There is exactly one ticker sponsorship. Once a bank takes it, it${AP}s gone. We brought it to you first.".replace("${AP}", AP)],
    ["03", "You already outgrew 20 screens", "You signed for 20 and you${AP}re on 65 venues. Going full network locks in everything you${AP}ve built — at a rate that won${AP}t hold forever.".split("${AP}").join(AP)],
  ];
  cards.forEach(([n, h2, b], i) => {
    const x = M + i * 4.04;
    s.addShape("roundRect", { x, y: 2.15, w: 3.75, h: 3.45, fill: { color: CARD }, rectRadius: 0.08, line: { type: "none" } });
    s.addText(n, { x: x + 0.32, y: 2.43, w: 3.1, h: 0.68, fontFace: FONT, fontSize: 40, bold: true, color: GOLD, margin: 0 });
    s.addText(h2, { x: x + 0.32, y: 3.18, w: 3.1, h: 0.62, fontFace: FONT, fontSize: 15.5, bold: true, color: WHITE, margin: 0 });
    s.addText(b, { x: x + 0.32, y: 3.84, w: 3.1, h: 1.65, fontFace: FONT, fontSize: 11.5, color: ICE, margin: 0, lineSpacingMultiple: 1.22 });
  });
  s.addText("SEP 1 — KICKOFF, TICKER LIVE      ·      NOV 15 — HOLIDAY TRAFFIC PEAKS      ·      JAN 1 — A FULL YEAR OF BOTH TOWNS, OWNED", {
    x: M, y: 6.3, w: 11.83, h: 0.4, align: "left", fontFace: FONT, fontSize: 11, bold: true, color: MUTE, charSpacing: 1.5, margin: 0 });
  footer(s, 11);
}

// ── 12 · CLOSE ───────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: NAVY2 };
  gsq(s, M, 0.62, 0.14);
  s.addText("NEXT STEPS", { x: M + 0.26, y: 0.47, w: 9, h: 0.42, fontFace: FONT, fontSize: 12, color: GOLD, charSpacing: 3, bold: true, margin: 0, valign: "middle" });
  s.addText(`We${AP}re neighbors. Let${AP}s talk like it.`, { x: M, y: 0.92, w: 11.8, h: 0.7, fontFace: FONT, fontSize: 32, bold: true, color: WHITE, margin: 0 });
  s.addText(`Fifteen minutes over coffee on the Square. We${AP}ll walk the plan, answer everything, and your ads never stop playing while we do the paperwork.`, {
    x: M, y: 1.78, w: 11.5, h: 0.6, fontFace: FONT, fontSize: 13.5, color: ICE, margin: 0, lineSpacingMultiple: 1.25 });

  const team = [
    ["T. Creed Cannon", "OWNER / MANAGING PARTNER", "(601) 201-8202", "creed@mctvofms.com", path.join(S, "team_creed.png")],
    ["Mary Michael Cannon", "OWNER / MANAGING PARTNER", "(662) 801-5677", "mmc@mctvofms.com", path.join(S, "team_mm.png")],
    ["Swayze Hollingsworth", "DIRECTOR OF SALES", "(662) 907-0404", "swayze@mctvofms.com", path.join(S, "team_swayze.png")],
  ];
  team.forEach(([name, title, phone, email, photo], i) => {
    const x = M + i * 4.04, y0 = 2.62, cw = 3.75, ch = 3.35;
    s.addShape("roundRect", { x, y: y0, w: cw, h: ch, fill: { color: "262B4D" }, rectRadius: 0.08, line: { type: "none" } });
    const ps = 1.3;
    s.addImage({ path: photo, x: x + (cw - ps) / 2, y: y0 + 0.32, w: ps, h: ps, rounding: true });
    s.addText(name, { x: x + 0.2, y: y0 + 1.78, w: cw - 0.4, h: 0.34, align: "center", fontFace: FONT, fontSize: 15, bold: true, color: WHITE, margin: 0 });
    s.addText(title, { x: x + 0.2, y: y0 + 2.14, w: cw - 0.4, h: 0.28, align: "center", fontFace: FONT, fontSize: 9.5, color: GOLD, charSpacing: 2, margin: 0 });
    s.addText(`${phone}\n${email}`, { x: x + 0.2, y: y0 + 2.5, w: cw - 0.4, h: 0.62, align: "center", fontFace: FONT, fontSize: 11, color: ICE, margin: 0, lineSpacingMultiple: 1.25 });
  });

  const lw2 = 1.9;
  s.addImage({ path: logoWhite, x: (W - lw2) / 2, y: 6.4, w: lw2, h: lw2 / LOGO_AR });
}

pres.writeFile({ fileName: OUT }).then(() => console.log("WROTE", OUT));
