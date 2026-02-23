# MCTV Elite Advertising - Analytics & Search Setup Guide

**For:** Creed (MCTV Elite Advertising)
**Site:** https://mctvofms.com
**Last Updated:** February 2026

This guide walks you through setting up Google Search Console, Google Analytics 4, and Google Business Profile for MCTVofMS.com. Follow each step in order. No coding required -- just follow the screenshots and instructions.

---

## Part 1: Google Search Console

Google Search Console (GSC) tells you how your site appears in Google search results, which keywords people use to find you, and whether Google is having trouble reading any of your pages. This is the single most important free SEO tool.

### Step 1: Create a Google Search Console Account

1. Go to [search.google.com/search-console](https://search.google.com/search-console)
2. Sign in with the Google account you want to own this property (use the same Google account you'll use for Analytics and Business Profile -- keeps everything in one place)
3. Click "Add property"

### Step 2: Verify Ownership (DNS TXT Record Method)

The DNS method is the best option because it verifies the entire domain (including all subdomains and https/http versions) in one step.

1. In Search Console, choose "Domain" (not "URL prefix") as the property type
2. Enter `mctvofms.com` (no https, no www -- just the domain)
3. Click "Continue"
4. Google will give you a TXT record that looks something like:
   ```
   google-site-verification=abcdef123456789
   ```
5. Copy that entire TXT record string
6. Log in to your domain registrar (wherever you bought mctvofms.com -- GoDaddy, Namecheap, Cloudflare, etc.)
7. Go to DNS settings for mctvofms.com
8. Add a new DNS record:
   - **Type:** TXT
   - **Host/Name:** @ (or leave blank, depending on registrar)
   - **Value:** Paste the google-site-verification string
   - **TTL:** Leave default (or set to 3600)
9. Save the record
10. Go back to Google Search Console and click "Verify"
11. If it doesn't verify immediately, wait 15-30 minutes and try again. DNS changes can take up to 48 hours but usually work within an hour.

### Step 3: Submit Your Sitemap

1. In Search Console, click "Sitemaps" in the left sidebar
2. In the "Add a new sitemap" field, enter: `sitemap_index.xml`
3. Click "Submit"
4. You should see the status change to "Success" within a few minutes
5. The sitemap URL being submitted is: `https://mctvofms.com/sitemap_index.xml`

**Note:** If you're using RankMath (which you should be), RankMath automatically generates this sitemap. You can check it by visiting https://mctvofms.com/sitemap_index.xml in your browser.

### Step 4: Request Indexing for All Pages

Google will eventually find all your pages through the sitemap, but you can speed things up by requesting indexing manually for your most important pages.

1. In Search Console, go to "URL Inspection" (top search bar)
2. Paste each URL one at a time and press Enter:
   - `https://mctvofms.com/`
   - `https://mctvofms.com/screen-advertising/`
   - `https://mctvofms.com/locations/`
   - `https://mctvofms.com/get-started/`
   - `https://mctvofms.com/solutions/`
   - `https://mctvofms.com/about-us/`
   - `https://mctvofms.com/contact-us/`
   - `https://mctvofms.com/website-design/`
   - `https://mctvofms.com/social-media-management/`
   - `https://mctvofms.com/social-media-ads/`
   - `https://mctvofms.com/pay-per-click-ppc/`
   - `https://mctvofms.com/connected-tv-ott-ads/`
   - `https://mctvofms.com/geofencing/`
   - `https://mctvofms.com/streaming-audio/`
   - `https://mctvofms.com/pre-roll-advertising/`
   - `https://mctvofms.com/youtube-ads/`
   - `https://mctvofms.com/google-business-profile/`
   - `https://mctvofms.com/design/`
   - `https://mctvofms.com/venue-partner/`
   - `https://mctvofms.com/samples/` (when live)
   - `https://mctvofms.com/faq/` (when live)
   - `https://mctvofms.com/oxford-advertising/` (when live)
   - `https://mctvofms.com/starkville-advertising/` (when live)
   - `https://mctvofms.com/tupelo-advertising/` (when live)
3. For each URL, after the inspection loads, click "Request Indexing"
4. Google limits this to about 10-12 requests per day, so you may need to spread this across 2-3 days

### Step 5: What to Check After 48 Hours

Come back to Search Console after 48 hours and check these things:

1. **Pages report** (left sidebar > "Pages"):
   - Look at "Indexed pages" -- this number should be growing toward 20+
   - Check "Not indexed" -- click into it to see which pages aren't indexed yet and why
   - Common issues: "Discovered - currently not indexed" (just wait), "Crawled - currently not indexed" (thin content, improve the page)

2. **Sitemaps** (left sidebar > "Sitemaps"):
   - Your sitemap should show "Success" status
   - The "Discovered URLs" number should match your page count

3. **Performance** (left sidebar > "Performance"):
   - This will be empty for the first few days
   - After a week, you'll start seeing which search queries bring up your site
   - Pay attention to "Impressions" (how many times you showed up) and "Clicks" (how many times someone clicked)

---

## Part 2: Google Analytics 4 (GA4)

GA4 tells you who is visiting your website, what pages they look at, where they came from, and what actions they take. This is how you'll measure whether your SEO and marketing efforts are working.

### Step 1: Create a GA4 Property

1. Go to [analytics.google.com](https://analytics.google.com)
2. Sign in with the same Google account you used for Search Console
3. Click the gear icon (Admin) in the bottom left
4. Click "Create" > "Property"
5. Fill in the details:
   - **Property name:** MCTV Elite Advertising
   - **Reporting time zone:** Central Time (US)
   - **Currency:** US Dollar (USD)
6. Click "Next"
7. Choose your business details:
   - **Industry category:** Marketing & Advertising
   - **Business size:** Small
8. Click "Next"
9. Choose your business objectives:
   - Select "Generate leads" and "Drive online sales" (these configure the default reports for a lead-gen business)
10. Click "Create"
11. Choose "Web" as the platform
12. Enter your website details:
    - **Website URL:** mctvofms.com
    - **Stream name:** MCTV Elite Website
13. Click "Create stream"
14. You'll see a Measurement ID that looks like: `G-XXXXXXXXXX` -- copy this and save it somewhere

### Step 2: Add the Tracking Code to WordPress

You have two good options. Pick whichever one feels easier.

#### Option A: Google Site Kit Plugin (Recommended)

This is the easiest method and also connects Search Console data directly into your WordPress dashboard.

1. In WordPress, go to Plugins > Add New
2. Search for "Site Kit by Google"
3. Install and activate it
4. Click "Start Setup"
5. Sign in with your Google account
6. It will ask to connect Google Analytics -- click "Connect"
7. Select the GA4 property you just created ("MCTV Elite Advertising")
8. Click "Complete setup"
9. Done -- the tracking code is now automatically added to every page

#### Option B: Paste into Divi Theme Header

If you don't want another plugin, you can paste the code directly.

1. In WordPress, go to Divi > Theme Options > Integration tab
2. In the "Add code to the head of your blog" box, paste this code (replace G-XXXXXXXXXX with your actual Measurement ID):

```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

3. Click "Save Changes"

#### Verify It's Working

1. Open your website in a browser: https://mctvofms.com
2. Go to GA4 > Reports > Realtime
3. You should see yourself as an active user within 30 seconds
4. If you don't see anything, wait 5 minutes and try clearing your browser cache

### Step 3: Set Up Conversion Events

Conversions tell GA4 which actions on your site actually matter for your business. Here's what to track:

#### Conversion 1: Get Started Page View (High Intent)

Someone who visits /get-started/ is seriously considering becoming a customer.

1. In GA4, go to Admin > Events
2. Click "Create event"
3. Event name: `view_get_started`
4. Matching conditions:
   - Parameter: `page_location`
   - Operator: `contains`
   - Value: `/get-started`
5. Click "Create"
6. Back on the Events list, find `view_get_started` and toggle "Mark as conversion" ON

#### Conversion 2: Samples Page View (Considering)

Someone viewing ad samples is evaluating your service.

1. Click "Create event" again
2. Event name: `view_samples`
3. Matching conditions:
   - Parameter: `page_location`
   - Operator: `contains`
   - Value: `/samples`
4. Click "Create"
5. Toggle "Mark as conversion" ON

#### Conversion 3: Intake Form Submission

If your intake form on /get-started/ triggers a thank-you page or URL change after submission:

1. Click "Create event"
2. Event name: `form_submit_intake`
3. Matching conditions:
   - Parameter: `page_location`
   - Operator: `contains`
   - Value: `/thank-you` (or whatever URL appears after form submission)
4. Click "Create"
5. Toggle "Mark as conversion" ON

**If there's no thank-you page redirect:** You'll need to track the form submit button click instead. The easiest way is to use Google Tag Manager (GTM) with a click trigger on the submit button. If this sounds complicated, Site Kit + the page-view method above is fine for now.

#### Conversion 4: Sample PDF Download

If you have downloadable sample PDFs on /samples/:

1. In GA4, go to Admin > Events
2. Click "Create event"
3. Event name: `download_sample_pdf`
4. Matching conditions:
   - Parameter: `link_url`
   - Operator: `contains`
   - Value: `.pdf`
5. Click "Create"
6. Toggle "Mark as conversion" ON

#### Conversion 5: MCTV Bot Tool Usage (External Link Click)

Track when someone clicks through to the MCTV Bot tool.

1. Click "Create event"
2. Event name: `click_mctv_bot`
3. Matching conditions:
   - Parameter: `link_url`
   - Operator: `contains`
   - Value: `mctv-bot.onrender.com`
4. Click "Create"
5. Toggle "Mark as conversion" ON

**Note:** GA4 automatically tracks outbound link clicks as the `click` event with a `link_url` parameter. The custom events above filter those clicks to the ones you care about.

### Step 4: Link GA4 to Search Console

This lets you see your Google search performance data right inside GA4.

1. In GA4, go to Admin > Product links > Search Console links
2. Click "Link"
3. Choose the Search Console property for mctvofms.com
4. Select your web data stream
5. Click "Submit"
6. Now in GA4 > Reports, you'll see a "Search Console" section with queries, landing pages, and more

---

## Part 3: Google Business Profile

Google Business Profile (GBP) is how your business shows up in Google Maps and the local "map pack" results. For a local advertising agency, this is critical. When someone searches "advertising agency Oxford MS," you want to show up in that map pack.

### Step 1: Claim or Create Your Profile

1. Go to [business.google.com](https://business.google.com)
2. Sign in with the same Google account
3. Search for "MCTV Elite Advertising" to see if a listing already exists
   - **If it exists:** Click "Claim this business" and follow the verification steps
   - **If it doesn't exist:** Click "Add your business to Google"
4. Enter your business information:
   - **Business name:** MCTV Elite Advertising
   - **Business category:** Advertising Agency (primary)
   - **Do you serve customers at this business address?** Choose based on whether you have a physical office clients visit. If you go to clients, choose "I deliver goods and services to my customers" and select service areas instead.

### Step 2: Verify Your Business

Google needs to verify you actually own this business. Options:

- **Phone verification:** Google calls or texts a code to your business phone (601-201-8202)
- **Postcard:** Google mails a postcard with a verification code to your address (takes 5-14 days)
- **Email:** Sometimes available if your domain email matches (creed@mctvofms.com)
- **Instant verification:** Sometimes available if you've already verified through Search Console

Choose whichever option Google offers you. Phone is fastest.

### Step 3: Complete Your Profile

Once verified, fill out every field completely. Google rewards complete profiles with better visibility.

**Business Information:**
- **Phone:** (601) 201-8202
- **Website:** https://mctvofms.com
- **Business hours:** Set your actual hours (e.g., Mon-Fri 8AM-5PM)

**Categories:**
- Primary: **Advertising Agency**
- Additional categories (add all of these):
  - Marketing Agency
  - Digital Advertising Service
  - Internet Marketing Service
  - Advertising Service

**Service Areas:**
Add these cities as your service areas:
- Oxford, MS
- Starkville, MS
- Tupelo, MS
- Water Valley, MS (if applicable)
- Batesville, MS (if applicable)
- Pontotoc, MS (if applicable)
- Add any other North Mississippi cities where you have screens

**Business Description:**
Write something like:
> MCTV Elite Advertising operates North Mississippi's largest indoor digital billboard network with screens in restaurants, gyms, salons, and clinics across Oxford, Starkville, and Tupelo. We also offer full-service digital marketing including website design, social media management, PPC advertising, connected TV ads, geofencing, and more. Contact us to learn how indoor billboard advertising can put your brand in front of thousands of local customers every month.

**Services:**
Add each service you offer as a listed service:
- Indoor Digital Billboard Advertising
- Website Design
- Social Media Management
- Social Media Advertising
- Pay-Per-Click (PPC) Advertising
- Connected TV & OTT Advertising
- Geofencing Advertising
- Streaming Audio Advertising
- Pre-Roll Video Advertising
- YouTube Advertising
- Google Business Profile Management
- Ad Design Services

### Step 4: Add Photos

Photos dramatically increase engagement with your profile. Upload these types:

- **Logo:** Your MCTV Elite Advertising logo (square format, at least 250x250px)
- **Cover photo:** Your best screen installation photo (landscape, at least 1080x608px)
- **Interior photos:** Photos of screens installed in venues (3-5 photos)
- **At work photos:** You or your team installing screens, meeting with clients (2-3 photos)
- **Team photos:** Professional headshot or team photo (1-2 photos)
- **Screen content examples:** Close-up shots of ads running on your screens (3-5 photos)

**Photo tips:**
- Use real photos, not stock photos
- Good lighting matters
- Show the screens in context (in the venue, with customers visible in the background)
- Add new photos monthly to keep the profile fresh

### Step 5: Start Posting Weekly

Google Business Profile has a "Posts" feature that works like a mini social media feed. Posting regularly signals to Google that your business is active and boosts your visibility.

**Post weekly. Here's a content calendar:**

| Week | Post Idea |
|------|-----------|
| Week 1 | New venue announcement: "We just installed screens at [Venue Name] in [City]! Another great location for our advertisers to reach customers." |
| Week 2 | Screen count milestone: "MCTV Elite now has [X] screens across North Mississippi. That's [X] locations where your brand can reach a captive audience." |
| Week 3 | Client win (no pricing): "Shoutout to [Business Name] for joining the MCTV Elite network! Their ad is now running on screens in [City]." |
| Week 4 | Service highlight: "Did you know we also offer [service]? Learn more at mctvofms.com/[service-page]/" |

**Important rules for posts:**
- Do NOT include pricing in posts
- Include a call to action: "Contact us at mctvofms.com/get-started"
- Keep posts under 300 words (shorter is better)
- Include a photo with every post
- Use the "Learn more" or "Sign up" button and link to the relevant page on your site

### Step 6: Get Reviews

Reviews are one of the biggest ranking factors for Google Business Profile. Start building them now.

1. In your GBP dashboard, find your "review link" (short URL that takes people directly to the review form)
2. Send this link to:
   - Current venue partners (ask them to review the experience of hosting a screen)
   - Current advertisers (ask them to review the advertising service)
   - Business contacts who know your work
3. Respond to every review -- positive and negative -- within 24 hours
4. Never offer incentives for reviews (this violates Google's terms)

---

## Part 4: Quick Wins Checklist

Everything above in priority order. Do these in this order for maximum impact with minimum effort.

| # | Task | Est. Time | Priority |
|---|------|-----------|----------|
| 1 | Verify mctvofms.com in Google Search Console (DNS method) | 20 min | Critical |
| 2 | Submit sitemap in Google Search Console | 2 min | Critical |
| 3 | Create GA4 property for mctvofms.com | 10 min | Critical |
| 4 | Install Site Kit plugin and connect GA4 | 10 min | Critical |
| 5 | Verify GA4 is tracking (check Realtime report) | 5 min | Critical |
| 6 | Claim/create Google Business Profile listing | 15 min | Critical |
| 7 | Verify GBP ownership (phone or postcard) | 5 min (+ wait) | Critical |
| 8 | Request indexing for top 10 pages in Search Console | 15 min | High |
| 9 | Set up "view_get_started" conversion event in GA4 | 5 min | High |
| 10 | Set up "view_samples" conversion event in GA4 | 5 min | High |
| 11 | Set up "click_mctv_bot" conversion event in GA4 | 5 min | High |
| 12 | Complete all GBP business information fields | 20 min | High |
| 13 | Add all business categories to GBP | 5 min | High |
| 14 | Add service areas to GBP (Oxford, Starkville, Tupelo) | 5 min | High |
| 15 | Upload logo and cover photo to GBP | 5 min | High |
| 16 | Upload 5-10 venue/screen photos to GBP | 15 min | High |
| 17 | Write and publish GBP business description | 10 min | High |
| 18 | Add all services to GBP service list | 10 min | High |
| 19 | Link GA4 to Search Console | 5 min | Medium |
| 20 | Request indexing for remaining pages in Search Console | 15 min | Medium |
| 21 | Set up "form_submit_intake" conversion event in GA4 | 10 min | Medium |
| 22 | Set up "download_sample_pdf" conversion event in GA4 | 5 min | Medium |
| 23 | Get review link from GBP and send to 5 venue partners | 10 min | Medium |
| 24 | Publish first GBP post (new venue announcement) | 10 min | Medium |
| 25 | Check Search Console Coverage report (after 48 hours) | 10 min | Medium |
| 26 | Set up weekly GBP posting schedule (calendar reminder) | 5 min | Medium |
| 27 | Check GA4 conversion events are firing correctly (after a few days of data) | 15 min | Medium |

**Total estimated time for all tasks: ~4.5 hours** (spread across a few days because some steps require waiting)

**If you only have 1 hour today, do items 1-7.** These are the foundation everything else builds on.

**If you have 2 hours, also do items 8-18.** This gets your analytics conversion tracking live and your Business Profile mostly complete.

**Everything else can be done in the following days** as verification processes complete and data starts flowing in.

---

## Helpful Links

- Google Search Console: https://search.google.com/search-console
- Google Analytics 4: https://analytics.google.com
- Google Business Profile: https://business.google.com
- Google Tag Manager (if needed later): https://tagmanager.google.com
- RankMath SEO Plugin Docs: https://rankmath.com/kb/
- Google's Schema Markup Tester: https://validator.schema.org/
- Google's Rich Results Test: https://search.google.com/test/rich-results

---

## What to Monitor Monthly

After everything is set up, check these things at least once a month:

1. **Search Console > Performance:** Are impressions and clicks growing? What new keywords are you appearing for?
2. **Search Console > Pages:** Are all your pages indexed? Any new errors?
3. **GA4 > Reports > Engagement:** Which pages get the most traffic? Where do people drop off?
4. **GA4 > Reports > Conversions:** How many people visit /get-started/ per month? Is the number growing?
5. **Google Business Profile > Insights:** How many people viewed your profile? How many called, visited your site, or asked for directions?
6. **Google Business Profile > Reviews:** Any new reviews to respond to?

Set a monthly calendar reminder: "Check MCTV analytics and GBP" -- takes about 15 minutes once you know where to look.
