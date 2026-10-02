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

### Added

- `layout_set: designed` in `brand.yaml`: the full set, plus a section label (`kicker:`) and a one-line `subtitle:` above and below every content-slide title, and five layouts built from shapes rather than loose text: `cards-3` and `cards-4` (a colored label band, bullets and a bold footer line per card), `process-4` and `process-5` (chevron steps in a primary-color ramp, a label inside each and text below), and `bands-3` (labeled rows that fill the slide). Comparison panels gain optional `left-logo` and `right-logo` slots. `generate.type.kicker` and `generate.type.lede` size the new lines. Every card, step and band is a required field, since its shape is drawn on the layout whether or not it has text. Other layout sets build exactly as before.
- Images with transparent pixels (logos, icons) fit inside their placeholder instead of being cropped to fill it, so a vendor logo is never cut.
- `tests/fixtures/demo-brands/designed/`: a deck on every designed-set layout, with transparent logos on the comparison panels and in image-right, built and rendered in all three demo brands generated with `layout_set: designed`.
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
