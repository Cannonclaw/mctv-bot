# The Canon Chronicle

A daily personal newspaper for Creed, compiled each morning by a Claude Code
Routine and published as a private Claude artifact. This directory holds the
design system the daily job reads — **no edition content ever lives in this
repo** (editions contain personal, financial, and calendar details and are
published only to the private artifact).

- **Live edition (private artifact):** https://claude.ai/code/artifact/e9d119df-6492-4573-982c-61ae8904f563
- **Schedule:** daily at 11:30 UTC (6:30 AM Central during CDT), via a
  Claude Code Remote Routine that spawns a fresh session per edition.
- **First edition:** Vol. I, No. 1 — Tuesday, July 7, 2026. Edition number =
  days since then + 1.

## How an edition is built

Four desks gather in parallel (background subagents), then the editor
compiles one page:

| Desk | Source | Beat |
|---|---|---|
| Gmail | Gmail MCP | Ole Miss, DOOH, Claude/Anthropic, action items, notable personal mail |
| Work | Microsoft 365 + Google Calendar MCP | Client/prospect/team activity, action items, week's calendar (times in Central) |
| Projects | Local repo + GitHub MCP | Recent commits, open PRs/issues, repo task signals, suggested priorities |
| News | WebSearch | Ole Miss football, DOOH industry, Claude Code/AI, north MS local business, sports business |

## Sections (in order)

1. **Masthead + vitals bar** — folio line, title, tagline, key numbers.
2. **Front page** — one lead story (the most consequential item of the day)
   plus one or two sidebars.
3. **The Docket** — the to-do list, ranked; the numbering *is* the priority.
   HIGH/MED/LOW pills. Unresolved items carry forward day to day.
4. **The Ledger** — standing goals, numbered with roman numerals, updated as
   they move.
5. **The Wire** — three news columns: Ole Miss Football, Out-of-Home,
   Claude Code & AI. Every item links a real source; unconfirmed items are
   labeled.
6. **The Works** — state of the MCTV Bot: shipping narrative, PR/issue
   stats, open checklist.
7. **Prospect Intelligence** — names worth a call, from local and
   sports-business news plus the work inbox.
8. **The Almanac** — the week's merged calendar, then "looking ahead."
9. **Colophon** — sourcing note.

## Design tokens

Defined in `template.html`. Newsprint ivory `#F2EDE3` / ink `#1C1A16`,
cardinal accent `#A3122E`, powder-blue secondary `#4E6E8A`; dark theme via
`prefers-color-scheme` plus `:root[data-theme]` overrides. Display face is
a Didot/Bodoni stack, body is Georgia, utility is a condensed sans.
Favicon is always 🗞️; artifact title format is
`The Canon Chronicle — <date>`.

## Rules for the daily job

- Only report facts actually found; never fabricate stories, emails, or URLs.
- Label single-sourced/unconfirmed items.
- Update the existing artifact URL above — never mint a new one.
- Personal/financial/medical details go only in the artifact, never into git.
- This job prints the paper; it does not push code changes.
