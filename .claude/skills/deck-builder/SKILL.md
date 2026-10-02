---
name: deck-builder
description: >-
  Builds branded, editable PowerPoint decks by driving the deterministic deck-builder CLI - the
  agent writes content (deck.md or a workbook) and the engine validates, builds, renders and
  measures. MUST be used whenever a deck, presentation, slides or a .pptx is to be created,
  drafted, updated, converted or bulk-generated in a repo where deck-builder is available,
  including from notes, markdown, a spreadsheet or a data file, and when converting a deck
  between markdown and Excel for team editing. Takes precedence over generic pptx tooling for
  creating decks. Not for reading or extracting text from an existing .pptx someone else made.
license: MIT
---

# deck-builder

You write content. The engine owns layout, styling and validation. Never write python-pptx code or
PowerPoint XML, never edit a built `.pptx`, and never change a brand kit (`brand.yaml`,
`tokens.yaml`, the template) unless the user asks. If the engine can't express something, tell
the user and propose an engine or brand-kit change.

## Preflight

- Inside the deck-builder clone, run the CLI as `uv run deck-builder`; elsewhere it's `deck-builder`
  (installed with `uv tool install`). Below, `db` stands for whichever applies.
- `db brand list` shows the brands. If it reports no config, run the `deck-onboard` skill first.

## Who does what

When the deck has to come out of more material than fits here (a folder of documents, a
knowledge base or vault), start with the `deck-decomposer-agent`: it returns `outline.md` (the
storyline with a source for every slide, plus open questions) and a draft `deck.md` that passes
`check`. Walk the user through the outline, co-author and proofread with them (or convert to
`.xlsx` for their team), and only then build.

For more than a handful of slides, hand the build loop to the `deck-builder-agent` subagent and
keep this context for the storyline and the review. Give it the source material paths, the brand
slug, the approved storyline, the deck's path and any constraints. It returns a short report;
run the review gate below before anything reaches the user.

## The loop

```
db brand show <slug>                # layouts, fields, budgets (kind<=chars, xN bullets, * required)
db docs deck-md                     # the deck.md format, once (or: db docs workbook)
db check <deck> --json              # validate; fix every issue; repeat until no errors
db check <deck> --render --json     # build, render and measure in one step
db explain <CODE>                   # cause and fix for any issue code
```

1. **Storyline first.** Slide titles only, one takeaway each. For more than 8 slides, or anything
   client-facing, get the user's OK before writing slides.
2. **Write to the budgets** from `brand show`. Choose layouts by content: one number is
   big-number, a comparison is two-col or comparison, a trend is chart.
3. **Fix by code, never by loosening rules.** Cut words, split the slide, change the layout, move
   detail to speaker notes. If a budget looks wrong, say so; the user changes the brand kit.
4. **Look at flagged slides only.** `check --render --json` returns `flagged_slides` (each with its
   `slide` number and `codes`), `contact_sheets`, and `slide_png` (the `slide-NN.png` pattern in
   `render_dir`). Open the PNGs for flagged slides and the contact sheets; a slide image costs
   about 1,200 tokens, so don't open every slide.
5. **Stop after three fix loops** and report what's still off.

Speaker notes hold the source of every number and anything cut from the slide.

## Review gate (main agent)

Before any deck reaches the user:

1. Run `db check <deck> --json` yourself; it must report no errors.
2. Read the subagent's report and the manifest (`<deck>.manifest.json` beside the `.pptx`).
3. Open the flagged slide PNGs and the contact sheets.
4. Approve, or send the work back naming the slide and the issue code.

Then report: output path, slide count, render backend, any slide you're unsure about, and any
number or source you couldn't verify.

## Reading output

- `--json` prints one object: `ok`, `issues[]` (`code`, `severity`, `file`, `line`, `slide`,
  `field`, `message`, `actual`, `limit`) plus keys such as `output`, `manifest`, `flagged_slides`.
- Exit 0 is success, 1 means issues to fix in content, 2 is a usage or environment problem: the
  object then has `error` and sometimes `code` (such as `UNKNOWN_BRAND`).
- `MISSING_FONT` means a brand font isn't installed where the deck rendered. Report it to the user;
  don't change content to fit the substitute font.
- `RENDER_UNVERIFIED` means the PowerPoint backend hasn't been verified on this Mac yet; say so.

## Other paths

- **Team editing in Excel:** `db convert deck.md deck.xlsx`, share it, then `db build deck.xlsx`.
  Converting back loses nothing; `convert` refuses with `CONVERT_LOSSY` rather than drop content.
- **Bulk, one deck per data row:** `{{column}}` tokens in the deck, then
  `db build deck.md --data rows.csv --name "{{client}}.pptx"`.
- **Assets:** `db assets <slug>` lists logo, icon and color ids; `![alt](brand:logo/<id>)` places a
  logo, `brand:icon/<id>` an icon, and deck images sit in the deck's `assets/` folder.
- **A layout the content needs but the brand lacks:** tell the user; the `deck-brand` skill adds
  layouts. Don't fake it with another layout's fields.
