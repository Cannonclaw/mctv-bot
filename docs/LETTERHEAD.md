# MCTV Letterhead Templates

Three Word letterheads built from the same brand assets the proposals and
contracts use, so a letter, a proposal, and a contract all look like they came
from the same company.

```
python scripts/generate_letterhead.py
```

Writes to `output/letterhead/` (gitignored): one `.docx` per variant plus a
matching `.pdf` proof when LibreOffice is installed.

## The three variants

| File | Paper | Header | Team details |
| --- | --- | --- | --- |
| `MCTV_Letterhead_editorial.docx` | Cream | Centered wordmark, letterspaced tagline, gold hairline | Footer: markets + one contact line |
| `MCTV_Letterhead_masthead.docx` | White | Full-bleed navy band, reversed-out wordmark, gold rule | Band: website, phone, email, markets |
| `MCTV_Letterhead_team.docx` | Cream | Wordmark left, tagline and website right, gold hairline | Footer: three headshots with title, direct phone, email |

**editorial** is the quietest — good for anything where the letter itself should
carry the weight (thank-you notes, renewal letters, formal correspondence).

**masthead** has the most presence. Best for cold outreach and anything a
prospect sees before they know who MCTV is.

**team** is the one with faces on it. Use it when the relationship is the point:
onboarding letters, host venue welcomes, anything a client will keep.

## Using them

Open the `.docx`, delete the sample letter in the body, and type. The header and
footer are locked to the page, so they repeat on page two and stay put no matter
how long the letter runs. Margins, type size, and line spacing are already set.

To turn one into a permanent template, save it as `.dotx` from Word
(File → Save As → Word Template) and double-clicking gives a fresh copy each time.

### Printing the cream stock

The cream is a page background. Word shows it on screen but does **not** print
backgrounds unless you turn that on:

> File → Options → Display → check **Print background colors and images**

The PDF proofs already have the cream baked in, so printing or emailing the PDF
needs no setting change. If you're printing on actual cream paper stock, use the
`.docx` with the background printing left off.

## Editing the design

- **Contact details, titles, phone numbers, markets** come from
  `config/config.json` (`company`, `team`, `markets`). Change them there and
  re-run the script — nothing is hardcoded in the layouts.
- **Mailing address** is off by default. Set `ADDRESS_LINE` at the top of
  `scripts/generate_letterhead.py` and it appears in all three footers.
- **Colors** are the same navy and gold as everywhere else, plus a steel blue
  sampled from the logo's own "ELITE ADVERTISING" line so the type matches the
  mark rather than approximating it.
- **Artwork** (`assets/letterhead/`) is derived from `assets/branding/` and
  `assets/team/` by `scripts/letterhead_assets.py`: the wordmark gets its white
  field stripped so it sits on cream, and headshots become circular crops with a
  gold hairline ring. Re-run that script after replacing a headshot.
