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

You write content. The engine owns layout, styling and validation. You never write python-pptx
code or PowerPoint XML, never edit a built `.pptx`, and never change a brand kit (`brand.yaml`,
`tokens.yaml`, the template) unless the user asks. If the engine can't express something,
tell the user and propose an engine or brand-kit change.

## Preflight

1. `deck-builder --version` must print 0.1.0 or later. If the command is missing, run it as
   `uv run deck-builder` from the deck-builder repo, or install it with `uv tool install`.
2. If `deck-builder brand list` reports no config or no brands, run the `deck-onboard` skill first.

## Who does what

For more than a handful of slides, hand the build loop to the `deck-builder-agent` subagent
and keep this context for the storyline and the review. Give it: the source material paths,
the brand slug, the approved storyline, the output path, and any constraints. It returns a
short report; you then run the review gate below before anything reaches the user.

## The loop

```
deck-builder brand show <slug>        # layouts, fields, budgets, palette, logo and icon ids
deck-builder docs deck-md             # the deck.md format (or: docs workbook)
deck-builder check <deck> --json      # validate; fix every issue, repeat
deck-builder build <deck> --json      # writes the .pptx and <deck>.manifest.json
deck-builder render <pptx> --json     # PDF, slide PNGs, contact sheets, flagged_slides
deck-builder explain <CODE>           # cause and fix for any issue code
```

1. **Storyline first.** List slide titles only, one takeaway each. For more than 8 slides, or
   anything client-facing, get the user's OK before writing slides.
2. **Write to the budgets** from `brand show`. Choose layouts by content: one number is a
   big-number slide, a comparison is two-col, a trend is a chart.
3. **Fix by code, never by loosening rules.** Edit content: cut words, split the slide, change
   the layout, move detail to speaker notes. Never raise a budget or delete a lint rule to pass;
   if a budget looks wrong, say so and let the user change the brand kit.
4. **Render and look at flagged slides only**, plus the contact sheets. Each slide image costs
   about 1,200 tokens, so don't open every slide.
5. **Stop after three fix loops** and report what's still off.

Speaker notes hold the sources for every number and anything cut from the slide.

## Review gate (main agent)

Before any deck reaches the user:

1. Run `deck-builder check <deck> --json` yourself; it must report zero errors.
2. Read the manifest and the subagent's report.
3. Open the flagged slide PNGs and the contact sheets.
4. Approve, or send the work back naming the slide and the issue code.

Then report: output path, slide count, any slide you're unsure about, and any number or source
you couldn't verify.

## Other paths

- **Team editing in Excel:** `deck-builder convert deck.md deck.xlsx`, share it, then
  `deck-builder build deck.xlsx`. Converting back to markdown loses nothing.
- **Bulk (one deck per data row):** a deck file with `{{column}}` tokens, then
  `deck-builder build template.md --data rows.csv --name "{{client}}.pptx"`.
- **A layout the content needs but the brand lacks:** tell the user; the `deck-brand` skill adds
  layouts. Don't fake it with another layout's fields.

## Reading output

`--json` prints one object: `ok`, `issues[]` (each with `code`, `file`, `line`, `slide`,
`field`, `message`, `actual`, `limit`) and command-specific keys such as `output`, `manifest`
and `flagged_slides`. Exit codes: 0 success, 1 validation issues, 2 usage or environment
problems. Without `--json`, output is one line per issue and one summary line.
