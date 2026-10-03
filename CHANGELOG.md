# Changelog

All notable changes to this project are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## Unreleased

### Changed

- Generated kits follow a design standard, described in the new `deck-builder docs design` topic. Type is sized for projection: bold 32 pt titles, 24 pt single-column body, 20 pt two-column text, 18 pt tables. Short single-column and two-column content sits at the optical center of its area instead of hugging the top. Comparison columns sit on tinted panels with the heading inside, and two-column slides get a thin divider. Title, section, closing and big-number slides get one short accent rule, bullets and agenda numbers take the primary color, and the agenda is a numbered list. Regenerate a kit with `brand init <slug> --force` to get the new look.
- Generated tables have a dark header, thin rules between rows and no vertical lines, with column widths that follow the content and numeric columns right-aligned. Bar and column charts with no negative values start their value axis at zero. `brand init` writes every table key to `tokens.yaml` (`row_fill`, `text`, `rule`, `row_height_factor`), and the row budget follows the placeholder height.
- The MCP server confines paths to the workspace and refuses the clone's own `src/`, `.claude/` and `.git/` folders and its `AGENTS.md`, `CLAUDE.md` and `deck-builder.toml`, whatever the config says, compared case-insensitively. Relative paths still resolve against the config folder. Paths the engine derives from an argument (the manifest beside a build, the render folder, import output, the deck file in a folder, discovered kits) pass the same check, and a symlinked kit is skipped.
- `auto` rendering prefers LibreOffice, the verified backend; `check` takes `--backend`.
- Rebuilding refuses to replace a .pptx that was edited after it was built, unless `--force`; the .pptx and its manifest are written together. Bulk builds refuse output names that collide.
- `brand adopt` keeps only masters, layouts and the theme from a .pptx, and drops external relationships and embedded objects; `import --adopt` never regenerates an existing kit. A kit holding both `template.potx` and `template.pptx`, or two fields on one placeholder, is invalid.
- Imported hyperlinks keep only http, https and mailto; imported notes that look like deck.md structure are escaped, and an import whose deck.md wouldn't reparse to the same slides fails with `IMPORT_LOSSY`.
- Charts are quieter: hairline gridlines in a faint tint, no tick marks, axis labels and the legend in the muted color (new `chart.axis_text_color`, which `brand init` writes with `gridline_color`), line charts with a heavier line and no markers, a hairline of the background between stacked segments, no label on a stacked segment too thin to hold one, and a small gap between the bars of one group. A bar or column chart with data labels drops its value axis and gridlines. Horizontal bar charts list their categories top to bottom in the order written. Regenerate a kit with `brand init <slug> --force` to get the new chart tokens.
- `docs design` shows shares of a whole as a sorted bar chart, not a pie or doughnut; the engine still builds both. The demo decks use bars for shares.
- README: an Example decks section after Write a deck holds the nine-slide grid, now chosen for color and range (pictures, three chart types, a title slide and shape layouts) from the demo brands' pitch and review decks.

### Added

- `statement` layout in the full and designed sets: one sentence in large type (40 pt projected, 28 pt read, `generate.type.statement`) for the turn of a story or the ask, its `**bold**` phrase in the primary color, set like `big-number` with the accent rule and an optional `caption:`.
- `check` warns `PROSE_TELL` on the countable writing tells in slide text: dash, curly quote, ellipsis and arrow characters, emoji, inflated words (leverage, seamless, robust), intensifiers standing in for a number, filler transitions, teaser phrases, and a third "X, not Y" contrast in one deck. Speaker notes, code and quoted words are left alone. `docs design` gains a "Writing on slides" section.
- `deck-storyteller-agent`, optional: turns an outline, data, a scenario or image cues into `storyboard.md`, the arc, the title spine, and each slide's layout, focal point, emphasis, visual and pacing, which the user approves as the storyline and the builder writes the deck from. It runs no commands. `deck-builder docs story` defines the storyboard and the storytelling rules (arcs, a map slide and its parts for long decks, slide-to-slide pacing, emphasis through layouts, picture, icon or chart). The builder, decomposer and brand agent can ask for it with a `Storyteller:` line in their reports. The storyteller, builder and validator prompts share one set of tone and style rules (plain words, no teasers, at most two "X, not Y" contrasts per deck, titles that state the point, every number sourced), and the validator reports breaches as findings.
- Code blocks with syntax highlighting. A fenced block with a language tag (```` ```python ````, `~~~`, CommonMark nesting, so a four-backtick block holds a markdown example with its own fence) is code. `{3,5-7}` highlights lines, `lines` adds line numbers and `title="etl.py"` a filename line. The new `code` and `code-right` layouts in the full and designed sets build it as editable text in the brand's code font: one run per token, highlighted by Pygments (a new dependency, pure Python and offline) into eight roles, keywords bold and comments italic, never wrapped, on a rounded panel trimmed to the code with a band behind highlighted lines. `brand init` writes `tokens.yaml` `code` (a light or dark panel from `generate.code.theme`, and a color per role from the palette, each held at 4.5:1 on the panel and the band) and `text.code_font` from `fonts.code` (default Menlo; code runs are marked fixed-pitch, so a machine without the font substitutes a monospace one), and `brand check` reports a code color under 4.5:1. `check` reports `CODE_LONG` for a line wider than the panel or more lines than it holds, `CODE_LANGUAGE` for a tag the highlighter doesn't know, and `CODE_LINES_MANY` past 12 lines on a projected slide, and `CODE_LONG` warns on an inline `code` span longer than a line of its field. `import` gives back the fenced block with its options, `convert` keeps it in a workbook cell and refuses it in CSV, and render QA measures code by its space-separated words. Dumbder Nifftlin's demo kit uses the dark panel, and its review deck's code slide is in the README grid. The default inline `code` font is now Menlo instead of Courier New.
- `layout_set: designed` in `brand.yaml`: the full set, plus a section label (`kicker:`) and a one-line `subtitle:` above and below every content-slide title, and layouts built from shapes rather than loose text: `cards-2` to `cards-5` (a colored label band, bullets and a bold footer line per card), `process-3` to `process-6` (chevron steps, a label inside each and text below), `bands-2` to `bands-4` (labeled rows that fill the slide) and `logos` (two to six logos with captions on one row, spaced evenly by the build). Comparison panels gain optional `left-logo` and `right-logo` slots. `generate.type.kicker` (18 pt, 12 pt read) and `generate.type.lede` size the new lines. Every card, step and band is a required field, since its shape is drawn on the layout whether or not it has text. The primary-color ramp on cards, steps and bands lightens only as far as white labels keep 4.5:1, worked out from each brand's colors. Other layout sets build as before.
- `generate` options for shapes, each defaulting to today's output: `takeaway: quote` (an italic line instead of the band), `icons.tile: square | circle` (icon-row icons drawn white on a primary tile), `bands.label_shape: rectangle`, `process.icons: true` (a white icon in each chevron, its title under it), and `emphasis: ink` (bold on cards and bands left in the text color instead of the primary).
- Starter icons: twelve alpha-mask icons (arrow, chart, check, clock, database, document, gear, layers, people, shield, star, warning) that any brand can place with `brand:icon/<id>` when its kit has no icon by that id. `brand show` and `assets` list them; `scripts/make_starter_icons.py` draws them.
- Front matter `kicker:` sets the section label on every slide that has one and sets none itself, and `first_slide_number:` numbers an excerpt of a larger deck from there.
- Images with transparent pixels (logos, icons) fit inside their placeholder instead of being cropped to fill it, so a vendor logo is never cut; in the image and image-right layouts a fitted logo takes at most 60% of the box, and logo slots fit any image.
- Accessibility to WCAG 2.2 AA, described in `docs design`: `brand check` reports the new color pairs the generated layouts use (`LOW_CONTRAST`), chart colors that look alike under simulated protanopia, deuteranopia or tritanopia (`CVD_CONFUSABLE`) and `generate.type` sizes under 18 pt projected or 12 pt read (`TYPE_SMALL`); `check` reports images without alt text (`MISSING_ALT`), duplicate slide titles (`TITLE_DUPLICATE`) and charts told apart by color alone (`COLOR_ONLY`).
- Warnings from the design research's working limits, labeled as convention: more than four bullets (`BULLETS_MANY`) or 60 words (`WORDS_MANY`) on a projected slide, more than three slides in a row on one layout (`LAYOUT_RUN`), and more than eight chart series (`SERIES_MANY`).
- `deck-validator-agent`: a read-only proofreader that signs off a built deck before the user sees it. It reads every rendered slide against `docs design` and returns PASS or SEND BACK with slide-by-slide fixes; the `deck-builder` skill's review gate runs it, and `skills install` links it.
- `tests/fixtures/demo-brands/designed/` and `options/`: decks on every designed-set layout and every `generate` option, built and rendered in all three demo brands.
- `tests/fixtures/demo-brands/decks/`: three decks per demo brand, each written in that brand's voice on its own kit configuration (designed defaults; read mode with square tiles, rectangle bands and ink emphasis; quote takeaways, circle tiles and process icons): a short pitch, a long data-heavy review, and an edge-case deck with fields at their budgets, special characters, nested markup, long tokens, negative and eight-series charts, two- and six-logo rows and starter icons. The tests check, build and render all nine.
- The neutral brand that `init` creates, and the three demo brands, use the designed set; each demo brand sets its own options in brand.yaml. The showcase deck, and so the README images, show cards, a chart under a section label and subtitle, bands, the logo row and icon tiles; a test checks the README's deck.md example on its brand and on neutral.
- `import` places a logo row's pictures left to right in its slots, since the build spreads them across the row.
- The demo brands' link color and icon color now meet WCAG contrast, and each has a fourth chart color of its own that stays apart from the others under simulated color blindness.
- `generate.mode: projected | read` in `brand.yaml`. Projected (the default) keeps every size at 18 pt or more, tables included. Read is for decks sent ahead and read on screen: 28 pt titles, a 14 pt body on a 9 in measure, 12 pt tables, text from the top.
- Table columns are at least as wide as their longest word, so no word breaks mid-word, and `TABLE_TALL` estimates with the same widths the build uses.
- `generate.type` in `brand.yaml` sets the type scale (title, title weight, subtitle, body, two-column, icon text, table, big number), and character budgets are computed from it. `generate.body_anchor: top` keeps body text at the top; `generate.big_number: dark` puts the big number on the primary color.
- An optional `takeaway:` field on content, two-column, chart and table slides: one sentence in a full-width band in the primary color at the bottom. Nothing is drawn when it's left out, and `import` gives it back only from a matching placeholder.
- `tests/fixtures/demo-brands/layouts/`: every generated layout with realistic content, built and rendered in all three demo brands. Two demo brands exercise `generate.type` and `big_number: dark`.
- Kits record what made them: `tokens.yaml` `generated:` holds the engine version and a hash of the brand.yaml sections and master logo that shape the template. `brand check` warns `KIT_STALE` when they change, and `brand init <slug> --force` regenerates a kit from its own brand.yaml.
- New issue codes: `TABLE_TALL` (a table estimated taller than its area), `STALE_BUILD` (the deck changed after its .pptx was built), `AMBIGUOUS_DECK` (a folder with two deck files), `IMPORT_LOSSY`, `KIT_STALE`.
- `render` and `check --render` report hidden slides and map PDF pages to the right slide numbers around them.
- `deck-builder docs agents`: one map of which agent owns each command and MCP tool; each subagent's tool allowlist names its MCP tools.
- `tests/scenarios/`: structurally different kits and decks run through the real CLI path, with per-step `--json` size budgets and byte-identical builds across workspaces.
- `doctor` warns when the `deck-builder` serving the agents' MCP tools is an editable install, since it then runs the clone's source live.
- The workspace folder roles are documented once (`workspace/README.md`, `docs workflow`): `source/` and `references/` for read-only inputs, `notes.md` for working notes, `scratch/` for disposable output. `init` creates `source/` in its example decks.

### Fixed

- Found by the brand fixture decks: negative bars drew as positive in LibreOffice (bar series now write `invertIfNegative` off) and covered their category names (the names now sit at the axis edge when a value is negative); `labels: true` on a doughnut showed nothing; labels on dark stacked segments and slices are white or ink by contrast; `kicker: ""` left an empty placeholder (an empty text field is now left out); `***bold italic***` printed its asterisks; a word the renderer split, matching another field's word exactly, was charged to that field as overflow; the designed set's kicker and subtitle shared placeholder idx 20 and 21 with the footer and slide number; a logo on a wide transparent canvas sat off-center (fitted images now crop their fully transparent margins); and a card's rule was drawn above an empty footer.
- Budgets come from the width text gets, less the side insets and a list's bullet indent, and generated kits record each text field's `line_chars` and `max_lines`, so `check` wraps the text line by line and reports `BUDGET_LINES` when short lines make bullets wrap past the box, which a character count can't see.
- A brand color under 3:1 as a chart color gets a darker shade of the same hue in the chart palette, so every bar and line meets WCAG 1.4.11 without a palette change.
- `deck-builder-agent`, the agent that writes slide content, reads `docs design` before writing; the decomposer, the brand agent and the skills already did. A test keeps every agent's MCP tools, install entry, role map entry and design reading in step.
- The content hash no longer depends on field order, so a deck converted to a workbook and back hashes the same.
- `skills install` run outside the clone links the clone the engine runs from (an editable install or `uv run --project`), instead of refusing.
- `brand add-asset --json` and the MCP `brand_add_asset` tool return `todo` with the `logos:` line a new logo needs, which only the human output showed before.
- The MCP `brand_init` tool takes no `from` with `force: true`, so an agent can regenerate a kit from its own `brand.yaml`, the fix for `KIT_STALE`.
- Image markdown on a `key:` line, such as `left-logo: ![alt](assets/x.png)`, fails with a message that names the `### left-logo` section to use instead of a bare YAML error.
- The workspace folder table is in `docs workflow`, so every workspace and every agent can read it; `workspace/README.md` existed only in the clone.

- Charts write `roundedCorners` off, which PowerPoint otherwise draws as rounded chart corners, and keep one color per series instead of varying colors across a single series.
- A `brand_paths` entry or a `workspace` value that resolves to the home folder, the filesystem root or a parent of the config folder is refused.
- Overflow measurement: tables are measured against their area, so table words no longer land on the footer and real overruns are reported; list numbers, a chart's own text and words a renderer splits mid-word are attributed correctly.
- Bold or italic around inline code renders; a low-resolution image flags its slide in `check --render`; the asset inventory refuses paths `check` refuses; extra plots in an imported combo chart are reported; front matter dates are validated; bulk values can't inject a field line.

### Docs

- The skills and agents route any edit to an existing deck through the `deck-builder` skill, use one delegation threshold and one two-round stop rule stated in AGENTS.md, treat engine changes during deck work as a separate task, cite grounding facts from outside the workspace in a dated `source/grounding-<date>.md`, and read `docs design` before writing slides.
- The help for `docs` and the MCP `docs` tool lists every reference topic, read from the topics themselves, so `design` and `agents` are no longer missing. `docs workflow` names `check --render` as the usual loop and covers import and bulk builds; `docs brand-yaml` and `docs design` describe the designed set and image fitting. The onboarding skill names LibreOffice as the verified renderer that `auto` prefers. The README command table lists `brand add-asset`, `schema` and `mcp`, and the Development section lists the maintainer scripts.
- README: `uv tool install .` is the main setup, with global skills and the clone as the other paths, and pipx or pip for machines without uv; a Design section; a Fix up an existing deck section for fonts, formatting and slide numbers.

## 0.1.0 - 2026-10-02

First release.

### Decks

- `deck.md`, `deck.xlsx` and `slides.csv` parse into one slide model. `convert` turns each into the others without loss and checks its output by parsing it back. Workbooks have a layout dropdown, live character counts and a README sheet.
- `check` validates budgets, field kinds, layouts, assets, lint rules, tables and charts, and reports each finding with a stable issue code. `explain <CODE>` prints its cause and fix.
- `build` fills template placeholders with inline markup, native charts and tables, logos and recolored icons, and writes a manifest. Rebuilds are byte-identical, and one deck builds the same file from any input format. `build --data` builds one deck per data row.
- `check` and `build` take a deck file or the folder holding it, and `build -o` takes a `.pptx` path or a folder.
- Slide numbers and an optional `footer:`, kept minimal: a 10 pt muted number on content slides. `slide_numbers: false` turns numbers off for a deck, and `generate.slide_numbers: false` for a brand.
- Charts and tables get alt text naming the chart type, title, series and categories, or the table's columns and row count.
- `table.status` in `tokens.yaml` maps cell values such as `Green`, `Amber` and `Red` to colors, and a matching cell gets a colored dot before its text.
- `import` turns an existing .pptx back into `deck.md`, its images and `import-report.md`, onto an existing brand (`--brand`) or one adopted from the file (`--adopt`). Local formatting is dropped and counted, content that can't be placed goes to the slide's notes and the report, and linked images are never fetched.

### Brands

- A brand kit is `brand.yaml`, `tokens.yaml`, a template and its assets, found by slug under the `brand_paths` in `deck-builder.toml` and validated against JSON Schemas that `schema` prints.
- `brand init` generates a 16:9 template and `tokens.yaml` from `brand.yaml` with a minimal, standard or full layout set. `brand adopt` wraps an existing template, and `brand add-asset` copies a logo or icon into a kit.
- `brand list`, `brand show`, `brand check`, `inspect` and `assets` show what a kit holds and verify it. `LOW_CONTRAST` warns when a color pair misses WCAG 2.2 contrast.
- `init` creates a workspace with the neutral brand and two example decks.

### Rendering and QA

- `render` uses LibreOffice, or PowerPoint for Mac (unverified, so it warns `RENDER_UNVERIFIED`), and writes a PDF, exact-size slide PNGs and contact sheets. It measures overflow, finds empty placeholders and missing fonts, and flags only the slides that need a look. `check --render` runs the whole loop in one step.
- `doctor` reports what the machine can do and prints the install command for anything missing.

### Claude Code

- `deck-onboard`, `deck-brand` and `deck-builder` skills, and the `deck-builder-agent`, `deck-brand-agent` and `deck-decomposer-agent` subagents. `skills install` links them into `~/.claude`.
- `deck-builder mcp` serves the CLI as MCP tools over stdio, confined to the workspace. The subagents have no shell and reach the engine only through it; the decomposer runs no commands.

### Security

- A deck reads images only inside its folder and a brand reads assets only inside its kit (`ASSET_OUTSIDE`). Front matter `output:`, `template:` and `tokens:` stay inside the deck's folder or the workspace, and a build never replaces a file it didn't make.
- Bulk data values can't add a line break or start a heading, image, fence or notes line (`BAD_DATA_VALUE`), whatever line separator they use.
- Template theme XML is parsed with entities, DTDs and network loads off.
- The MCP server refuses NUL bytes in paths and keeps argparse output off its stdout stream.

### Tooling

- CI runs lint, type checks, tests, a dependency audit and the render tier on pushes to `main`, pull requests and weekly. Dependabot keeps the lockfile and the Actions current.
- Three fictional demo brands and a showcase deck in `tests/fixtures/demo-brands/`; `scripts/readme_images.py` regenerates the README images from them.
