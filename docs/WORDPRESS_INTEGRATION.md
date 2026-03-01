# WordPress Integration Guide — MCTV Bot

> **Last updated:** 2026-02-27
> **Author:** Claude Code
> **Site:** mctvofms.com (WordPress + Divi)
> **Bot:** bot.mctvofms.com (Streamlit on Render)

---

## Overview

Two Streamlit pages are designed for public WordPress embedding:

| Page | URL | Purpose |
|------|-----|---------|
| Intake Form | `https://bot.mctvofms.com/Intake` | Lead capture form |
| Sample Proposals | `https://bot.mctvofms.com/Samples` | Downloadable sample PDFs |

Both pages hide the Streamlit sidebar, header, footer, and menu — they render as clean, standalone content suitable for iframe embedding.

---

## Quick Start (2 Minutes)

### Option A: Divi Code Module (Recommended)

1. Edit a page in Divi Visual Builder
2. Add a **Code** module
3. Paste the embed code below
4. Save & publish

### Option B: WordPress Block Editor

1. Edit a page in Gutenberg
2. Add a **Custom HTML** block
3. Paste the embed code below
4. Save & publish

---

## Embed Code: Intake Form

Create a new WordPress page at `/get-started/` or `/advertise/`.

```html
<!-- MCTV Intake Form Embed -->
<div class="mctv-embed-container">
  <iframe
    src="https://bot.mctvofms.com/Intake"
    title="Request Your Free MCTV Advertising Proposal"
    style="width: 100%; height: 1850px; border: none; border-radius: 8px;"
    loading="lazy"
    allow="clipboard-write"
  ></iframe>
</div>

<style>
.mctv-embed-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 16px;
}

/* Responsive height adjustments */
@media (max-width: 768px) {
  .mctv-embed-container iframe {
    height: 2100px !important;
  }
}

@media (max-width: 480px) {
  .mctv-embed-container iframe {
    height: 2400px !important;
  }
}
</style>
```

---

## Embed Code: Sample Proposals

Create a new WordPress page at `/samples/` or `/sample-proposals/`.

```html
<!-- MCTV Sample Proposals Embed -->
<div class="mctv-embed-container">
  <iframe
    src="https://bot.mctvofms.com/Samples"
    title="Download Sample MCTV Advertising Proposals"
    style="width: 100%; height: 1400px; border: none; border-radius: 8px;"
    loading="lazy"
  ></iframe>
</div>

<style>
.mctv-embed-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 16px;
}

@media (max-width: 768px) {
  .mctv-embed-container iframe {
    height: 1600px !important;
  }
}

@media (max-width: 480px) {
  .mctv-embed-container iframe {
    height: 1800px !important;
  }
}
</style>
```

---

## Embed Code: Full-Width (No Max-Width Constraint)

If your Divi layout already handles width, use this simpler version:

```html
<iframe
  src="https://bot.mctvofms.com/Intake"
  title="MCTV Intake Form"
  style="width: 100%; height: 1200px; border: none;"
  loading="lazy"
  allow="clipboard-write"
></iframe>
```

---

## Recommended Page Structure

### Page: "Get Started" (`/get-started/`)

**Divi Layout:**
1. **Section 1** — Hero banner (Divi native)
   - Heading: "Get Your Free Advertising Proposal"
   - Subtext: "Fill out the form below and we'll create a custom proposal for your business — usually within 24 hours."
   - Background: Navy (#1B1F3B) with gold (#C5A55A) accent
2. **Section 2** — Code Module with Intake iframe embed
3. **Section 3** — Divi CTA (optional)
   - "Questions? Call (662) 801-5677"

### Page: "Sample Proposals" (`/sample-proposals/`)

**Divi Layout:**
1. **Section 1** — Hero banner (Divi native)
   - Heading: "See What Your Proposal Looks Like"
   - Subtext: "Download free sample proposals for restaurants, salons, gyms, and auto shops."
2. **Section 2** — Code Module with Samples iframe embed

---

## Navigation Menu

Add these pages to the WordPress main menu:

| Menu Item | URL | Position |
|-----------|-----|----------|
| Get Started | `/get-started/` | Primary CTA (button style) |
| Sample Proposals | `/sample-proposals/` | Under "Resources" or top-level |

**Divi Menu Button Style (for "Get Started"):**
In Appearance > Menus, add a CSS class to the "Get Started" item:
- Class: `mctv-cta-button`

Then add this CSS in Divi > Theme Options > Custom CSS:

```css
/* Gold CTA button in nav */
.mctv-cta-button > a {
  background-color: #C5A55A !important;
  color: #FFFFFF !important;
  padding: 8px 20px !important;
  border-radius: 4px !important;
  font-weight: 600 !important;
  transition: background-color 0.3s ease !important;
}

.mctv-cta-button > a:hover {
  background-color: #B39347 !important;
}
```

---

## Auto-Resize Iframe (Optional Enhancement)

If you want the iframe to auto-resize to fit its content (eliminates scrollbars):

```html
<iframe
  id="mctv-iframe"
  src="https://bot.mctvofms.com/Intake"
  title="MCTV Intake Form"
  style="width: 100%; border: none; min-height: 800px;"
  loading="lazy"
  allow="clipboard-write"
></iframe>

<script>
// Auto-resize iframe to content height
window.addEventListener('message', function(e) {
  if (e.origin !== 'https://bot.mctvofms.com') return;
  if (e.data && e.data.type === 'streamlit:height') {
    document.getElementById('mctv-iframe').style.height = e.data.height + 'px';
  }
});
</script>
```

> **Note:** This requires Streamlit to post height messages, which it does
> natively in some configurations. If it doesn't work, the fixed-height
> approach above is perfectly fine.

---

## SEO Considerations

Both embedded pages already include:
- `<meta name="description">` tags
- Open Graph tags (`og:title`, `og:description`, `og:url`)
- Twitter Card tags
- JSON-LD structured data (WebPage + LocalBusiness/Service schemas)
- Canonical URLs (`bot.mctvofms.com/Intake`, `bot.mctvofms.com/Samples`)

**For the WordPress wrapper pages**, add via Rank Math:
- **Intake page:** Focus keyword "indoor digital billboard advertising Mississippi"
- **Samples page:** Focus keyword "MCTV sample proposals"
- Set canonical to the WordPress URL (not the bot URL) since WordPress is the primary

---

## Troubleshooting

### Iframe doesn't load
- Verify `bot.mctvofms.com` is online (check Render dashboard)
- The Streamlit config already has `enableXsrfProtection = false` and `enableCORS = false`

### Iframe shows scrollbars
- Increase the `height` value in the iframe style
- Mobile needs more height (form fields stack vertically)

### Download buttons don't work inside iframe
- Streamlit download buttons work inside iframes by default
- If blocked, add `sandbox="allow-downloads allow-same-origin allow-scripts"` to the iframe

### Content looks too narrow / wide
- The `max-width: 800px` container keeps content readable
- Remove the container div if your Divi section already constrains width

### Mixed content warning
- Both sites use HTTPS — this should not occur
- Verify WordPress is forcing HTTPS (check SiteGround SSL settings)

---

## Checklist

- [ ] Create WordPress page "Get Started" at `/get-started/`
- [ ] Paste Intake iframe embed code
- [ ] Create WordPress page "Sample Proposals" at `/sample-proposals/`
- [ ] Paste Samples iframe embed code
- [ ] Add both pages to nav menu
- [ ] Style "Get Started" as CTA button in nav
- [ ] Set Rank Math SEO for both pages
- [ ] Test on desktop, tablet, mobile
- [ ] Verify PDF downloads work through iframe
- [ ] Verify form submission works through iframe
