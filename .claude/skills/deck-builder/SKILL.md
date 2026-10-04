---
name: deck-builder
description: >-
  Builds branded, editable PowerPoint decks by driving the deterministic deck-builder CLI: the
  agent writes content (deck.md or a workbook); the engine validates, builds, renders and
  measures. MUST be used whenever a deck, presentation, slides or a .pptx is created, drafted,
  updated, converted or bulk-generated, including from notes, markdown, a spreadsheet or a data
  file; when converting between markdown and Excel; when an existing .pptx is refreshed,
  re-branded or cleaned up (consistent fonts, colors, slide numbers, via import); and whenever an
  existing deck.md or workbook is restructured, reordered, aligned, synced, reconciled, compared,
  revised, tightened or otherwise edited. Preferred over generic pptx tooling. Not for just reading
  or quoting text from a .pptx someone else made.
license: MIT
---

# deck-builder

You write content. The engine owns layout, styling and validation. Never write python-pptx code or
PowerPoint XML, never edit a built `.pptx`, and never change a brand kit (`brand.yaml`,
`tokens.yaml`, the template) unless the user asks. If the engine can't express something, tell
the user: styling goes into the brand kit; an engine change under `src/` is a separate task the
user has to ask for explicitly (see AGENTS.md).

## Preflight

- Inside the deck-builder clone, run the CLI as `uv run deck-builder`; elsewhere it's `deck-builder`
  (installed with `uv tool install`). Below, `db` stands for whichever applies.
- `db brand list` shows the brands. If it reports no config, run the `deck-onboard` skill first.
- `db <command> --help` lists every flag a command takes; this skill names only the ones the loop uses.

## Who does what

When the deck has to come out of more material than fits here (a folder of documents, a
knowledge base or vault), start with the `deck-decomposer-agent`. It runs no commands, since what
it reads is untrusted, so put the output of `brand show <slug> --json`, `docs deck-md` and
`docs design` in its prompt. It returns `outline.md` (the storyline with a source for every slide, plus open questions)
and a draft `deck.md`; run `check` on the draft and send any issues back to the same agent (SendMessage), up to two rounds,
then report what's left to the user. Walk the user through the outline, co-author and proofread
with them (or convert to `.xlsx` for their team), and only then build.

Run the `deck-storyteller-agent` when a subagent's report ends with a `Storyteller:` line, when a
deck has to persuade or the user wants it to land harder, or when an outline mixes data, scenarios
and image cues with no clear arc. It runs no commands, so put the inputs' paths, the audience and goal,
the slide count, the tone (`plain` unless the user asks for `warm` or `bold`), the deck folder and the
output of `brand show <slug> --json`, `docs story` and `docs design` in its prompt. It writes
`storyboard.md`: the title spine and each slide's layout, focal point, emphasis and visual. Walk the
user through it as the storyline, with the image cues they need to supply; once they approve it, it
is the approved storyline you give the builder and, at the review gate, the validator.

At AGENTS.md's delegation threshold, hand the build loop to the `deck-builder-agent` subagent and
keep this context for the storyline and the review. Give it the source material paths, the brand
slug, the approved storyline, the deck's path and any constraints. It has no shell and runs the
engine through five MCP tools, which work only inside the workspace, so every path you give it must
be there (the full command and tool map is `db docs agents`). It returns a short report; run the
review gate below before anything reaches the user.

## The loop

```
db brand show <slug>                # layouts, fields, budgets (kind<=chars, xN bullets, * required)
db docs deck-md                     # the deck.md format, once (or: db docs workbook)
db docs design                      # which layout fits which point, and how much goes on a slide
db check <deck> --json              # validate; fix every issue; repeat until no errors
db check <deck> --render --json     # build, render and measure in one step
db explain <CODE>                   # cause and fix for any issue code
```

1. **Storyline first.** Slide titles only, one takeaway each. At AGENTS.md's delegation
   threshold, or for anything client-facing, get the user's OK before writing slides.
2. **Write to the budgets** from `brand show`. Choose layouts by content, using the table in
   `docs design`: one number is big-number, a comparison is two-col or comparison, a trend is
   chart, three parallel actions are icon-row; on a designed-set brand, parallel options are cards,
   steps are process, and labeled themes are bands. Don't run table after table or list after
   list. Put the conclusion of a chart or table slide in `takeaway:`. Where the layouts have a
   `kicker:`, give every content slide one (a front matter `kicker:` sets the deck-wide default),
   and add a `subtitle:` where the title alone doesn't make the point.
3. **Fix by code, never by loosening rules.** Cut words, split the slide, change the layout, move
   detail to speaker notes. If a budget looks wrong, say so; the user changes the brand kit.
4. **Look at flagged slides only.** `check --render --json` returns `flagged_slides` (each with its
   `slide` number and `codes`), `contact_sheets`, and `slide_png` (the `slide-NN.png` pattern in
   `render_dir`). Open the PNGs for flagged slides and the contact sheets; a slide image costs
   about 1,200 tokens, so don't open every slide.
5. **Stop after two fix loops** and report what's still off.

Speaker notes hold the source of every number and anything cut from the slide.

## Review gate (main agent)

Before any built deck reaches the user:

1. Run `db check <deck> --json` yourself; it must report no errors. The loop's last step already
   rendered the deck, so add `--render` only when the deck changed after that render.
2. Read the builder's report (when a subagent built it) and the manifest (`<deck>.manifest.json`
   beside the `.pptx`).
3. Hand the deck to the `deck-validator-agent`: the deck's path, the brand slug, the `render_dir`
   (from the builder's report or your last render), the warnings from step 1, and the approved
   storyline (the `storyboard.md` path when there is one). It reads every rendered slide against
   `docs design`, writes nothing, and returns `VERDICT: PASS` or `SEND BACK` with `severity | slide |
   field | finding | fix` lines.
4. On SEND BACK, give its blocker and major findings to the same `deck-builder-agent` (continue it
   with SendMessage, so it keeps what it has read) or fix them here, then validate again. Up to two
   send-backs per deck; after that, report what's unresolved instead. Pass its engine or brand
   findings to the user, since they aren't content fixes.

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

## Edit or restructure an existing deck

Restructuring, reordering, aligning, syncing, reconciling, comparing, revising or tightening a
deck.md or workbook is still this skill. Back up first: commit the workspace repo, or copy
`deck.md` into `scratch/`. When `deck.md` already exists, edit it; never `import` over it. After
a restructure, report a slide-mapping table: old slide, new slide, what changed.

## A deck made with an older version

After the user updates deck-builder, run `db doctor` once, then `db check <deck> --json` on each deck
before editing it. These are the results an older deck can show:

- `KIT_STALE`: an older version made the brand kit. The kit still builds as before, without the newer
  layouts and styling. Upgrading it is the user's call, and the `deck-brand` skill does it; the kit as
  it was is kept in its `backups/` folder. Afterward, `db brand show <slug>` lists the layouts and
  `db docs design` says what each is for.
- `KIND_MISMATCH` on text that holds a fenced code block: that's a code block now, so move it to a
  `code` slide or make it inline code.
- Warnings such as `PROSE_TELL` or `CODE_LONG`: fix the ones the user wants fixed, and leave text
  they didn't ask about.
- A rebuild can look different from the old `.pptx` (quieter charts, code in Menlo). Render it and
  show the user before they replace a file they've already sent.

## Fix up or re-brand an existing .pptx

Use this for "fix the fonts", "align the formatting", "fix the slide numbers", "make this deck
match our brand", or a deck with many contributors that should look like one. The engine never
edits the old file in place: `import` turns it back into `deck.md`, and the rebuild takes every
font, size, color and position from the brand, with slide numbers on every content slide
(`slide_numbers: false` in front matter turns them off). The original .pptx is never modified.
If the source folder holds both a `.pptx` and a `.pdf` of the same deck, the `.pptx` is the
content source for `import`; the `.pdf` is the visual reference, since a LibreOffice render can
substitute fonts.

1. `db import <deck.pptx> <folder> --brand <slug>` maps it onto an existing kit (also how a deck is
   re-branded). `--adopt <new-slug>` instead makes a kit from the file's own masters and layouts.
2. Read `<folder>/import-report.md` with the user. It names each slide's layout and how it matched,
   what couldn't be placed, and the formatting that was dropped on purpose. Unplaced content sits in
   each slide's notes under "Unplaced from the original:".
3. Resolve each unplaced item and every budget issue by editing `deck.md`: move content into a
   field, split the slide, or cut it with the user's OK. Then `db check <folder> --json` until clean.
4. `db check <folder> --render --json`, and `db render <deck.pptx>` for the original.
5. Show the old and new contact sheets side by side, and report a slide-mapping table: old
   slide, new slide, what changed.

## Other paths

- **Team editing in Excel:** `db convert deck.md deck.xlsx`, share it, then `db build deck.xlsx`.
  Converting back loses nothing; `convert` refuses with `CONVERT_LOSSY` rather than drop content.
- **Bulk, one deck per data row:** `{{column}}` tokens in the deck, then
  `db build deck.md --data rows.csv --name "{{client}}.pptx"`.
- **Assets:** `db assets <slug>` lists logo, icon and color ids; `![alt](brand:logo/<id>)` places a
  logo, `brand:icon/<id>` an icon, and deck images sit in the deck's `assets/` folder.
- **A layout the content needs but the brand lacks:** tell the user; the `deck-brand` skill adds
  layouts. Don't fake it with another layout's fields.
- **A fact from outside the workspace** (another repo, a live system, a conversation): before it
  reaches a slide, write it into `decks/<slug>/source/grounding-<date>.md`, one citation per fact
  (file and lines, or code path and lines) and a `current` or `proposed` tag, so a slide never
  presents a plan as fact.
