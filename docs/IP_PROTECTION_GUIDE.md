# IP Protection Guide — MCTV Digital, Inc.

## What's Already Done

- [x] **GitHub repo is PRIVATE** — confirmed (returns 404 to public API)
- [x] **Copyright headers** on all 61 Python source files — `(c) 2026 MCTV Digital, Inc.`
- [x] **LICENSE file** — proprietary license, no open-source permissions granted
- [x] **TRADE_SECRETS.md** — formal registry of 9 trade secret categories (gitignored, stays local)
- [x] **Terms of Service** — portal page at `/portal_terms` covering IP, data, e-signatures, SMS, privacy
- [x] **Copyright footer** — visible on portal login and main app sidebar
- [x] **.gitignore** — TRADE_SECRETS.md excluded from repo

---

## What You Need to Do (Manual Steps)

### Step 1: Register Copyright with U.S. Copyright Office (~$65)

**Why:** Registration is required to file a lawsuit and unlocks statutory damages up to $150K per infringement.

**How:**
1. Go to: https://www.copyright.gov/registration/
2. Click "Register a Work" and create an account at https://eco.copyright.gov/
3. Select category: **Literary Work** (software is classified as literary work)
4. Fill in:
   - Title: "MCTV Bot — Advertising Management Platform"
   - Author: T. Creed Cannon (or MCTV Digital, Inc. if work-for-hire)
   - Year of creation: 2026
   - Year of publication: 2026
   - Nature of authorship: "Computer program"
5. Upload a deposit copy — you can submit a portion of the source code (first 25 pages and last 25 pages, with trade secrets redacted/blocked out)
6. Pay the $65 filing fee
7. Processing takes 3-8 months — you're protected from the filing date

**Tip:** You can redact/block out up to 50% of the deposited code to protect trade secrets. The Copyright Office calls this "Special Relief" — check the box for trade secret material.

### Step 2: Consider Trademark Filing (~$250-$350)

**Why:** Prevents competitors from using confusingly similar names in your industry.

**What to trademark:**
- "MCTV Elite Advertising" (your brand name)
- Your MCTV logo (separate filing)

**How:**
1. Search first: https://tmsearch.uspto.gov/ — make sure nobody else has it
2. File at: https://www.uspto.gov/trademarks/apply
3. Select: Class 035 (Advertising services) and/or Class 038 (Telecommunications)
4. Filing fee: $250/class (TEAS Plus) or $350/class (TEAS Standard)
5. Timeline: 8-12 months for approval
6. You can file yourself — no attorney required, though one helps

### Step 3: Get an IP Attorney Consult ($200-$400 for 1 hour)

**Why:** Confirm your strategy, review the ToS, and get advice specific to Mississippi law.

**What to bring:**
- This IP_PROTECTION_GUIDE.md
- TRADE_SECRETS.md
- Your LICENSE file
- The Terms of Service page
- A brief description of how the software was built (AI-assisted with substantial human direction)

**What to ask:**
1. Is our copyright claim strong given AI-assisted development?
2. Should we register as work-for-hire or individual authorship?
3. Are our Terms of Service sufficient for the portal?
4. Do we need an NDA template for contractors/partners?
5. Should we pursue patent protection for any of our processes?
6. Any Mississippi-specific considerations we should know about?

**Finding an attorney:**
- Mississippi Bar Association referral: https://www.msbar.org/for-the-public/lawyer-directory/
- Search for "intellectual property attorney Mississippi" or "technology attorney Oxford MS"
- Larger firms in Jackson (Butler Snow, Bradley) have IP practices
- For a small business, a 1-hour consult is usually sufficient to validate your approach

### Step 4: NDAs for Contractors/Partners

If anyone outside the core team (Creed, Mary Michael, Swayze) ever accesses the codebase:
- They must sign a Non-Disclosure Agreement before seeing any code
- Include IP assignment clause — anything they build for MCTV belongs to MCTV
- Template NDA resources: https://www.lawdepot.com/contracts/nda/ (or ask your IP attorney)

---

## Ongoing Maintenance

- [ ] **Quarterly review** of TRADE_SECRETS.md — update as new features are added
- [ ] **Annual copyright notice update** — bump the year in all headers each January
- [ ] **Access audit** — review who has access to GitHub, Supabase, Render
- [ ] **Contractor tracking** — log anyone who accesses the codebase and their NDA status
- [ ] **Competitive monitoring** — watch for similar products in the Mississippi market

---

## Key Legal References

- **Copyright Act:** 17 U.S.C. 101 et seq.
- **Defend Trade Secrets Act (DTSA):** 18 U.S.C. 1836
- **Mississippi Uniform Trade Secrets Act:** Miss. Code Ann. 75-26-1 et seq.
- **Mississippi UETA (Electronic Signatures):** Miss. Code Ann. 75-12-1 et seq.
- **Federal E-SIGN Act:** 15 U.S.C. 7001
- **TCPA (SMS Compliance):** 47 U.S.C. 227
- **U.S. Copyright Office AI Guidance (2025):** https://www.copyright.gov/ai/

---

*Document prepared February 24, 2026. This is not legal advice — consult a qualified attorney for legal guidance specific to your situation.*
