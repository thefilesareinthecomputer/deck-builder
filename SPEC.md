# deck-builder: project spec

Status: draft v0.4, 2026-10-01. Supersedes `deck-builder-SPEC.md` v0.3.
Owner: the repo owner. Deciders for open items are named in [section 20](#20-open-decisions).

## 1. Purpose

deck-builder turns structured content into branded, fully editable PowerPoint files that follow a fixed template. It's a deterministic, configurable alternative to freeform AI slide design, for people who have to ship real decks in a real template on a deadline.

The repo is self-contained. A new user clones it, opens Claude Code in it, and onboarding takes them from a fresh clone to a first built deck. The same `deck-builder` CLI serves people and agents: the embedded skills and the `deck-builder-agent` subagent call the CLI exactly as a person would.

### 1.1 Goals

- Native, editable PPTX: real text in template placeholders, native charts and tables. No image-only slides.
- Design lives in the brand kit (template, `brand.yaml`, `tokens.yaml`), never in LLM output.
- Deterministic: the same inputs produce a byte-identical file.
- Markdown and spreadsheet inputs are equal and convert into each other without loss.
- Brands are durable, discoverable and callable by name.
- Agent-friendly: terse output, `--json`, stable issue codes, a measured overflow check, and a manifest of every build.
- The engine is fully local: no network calls, no telemetry.

### 1.2 Non-goals

- Reproducing PowerPoint's text layout engine.
- Animations, transitions, SmartArt, video.
- Google Slides or Keynote output. Both open PPTX; native output is out of scope.
- A GUI.
- Windows automation of PowerPoint.

## 2. Division of labor

The engine does everything that can be decided by rules. The LLM does what needs judgment, and its output is always a text file that the engine then validates.

| Engine (deterministic, no LLM) | LLM (judgment) |
|---|---|
| Parsing `deck.md`, `.xlsx` and `.csv` into one slide model | Turning source notes into a storyline and slide text |
| `convert` between markdown and workbook | Choosing a layout per slide from the brand's layouts |
| Validating budgets, kinds, references, lint rules | Fixing reported issues by editing content: cutting, splitting, changing layouts |
| Building the PPTX from template placeholders | Reviewing flagged slides and contact sheets; approving or returning work |
| Rendering, measuring overflow, checking fonts | Writing `brand.yaml` with the user from a brand guide, site or existing deck |
| `inspect`, `brand init`, `brand adopt`, `assets`, `doctor` | Running onboarding with the user |

The LLM never writes PowerPoint XML or python-pptx code and never positions shapes. If the engine can't express something, the LLM proposes an engine or brand-kit change to the user.

## 3. System parts

| Part | Location | Contains |
|---|---|---|
| Engine | `src/deck_builder/` | Python package and the `deck-builder` CLI. No brand or client content. |
| Claude Code layer | `CLAUDE.md`, `.claude/skills/`, `.claude/agents/` | Onboarding instructions, three skills, one subagent. No code. |
| Workspace | `workspace/` (gitignored) | The user's brands, decks, output and cache |
| Examples | `src/deck_builder/data/` | The neutral example brand source and fictional example decks, copied into the workspace by `init` and used by tests |

Client material never enters tracked files. Example content uses invented companies only.

## 4. Configuration and workspace

### 4.1 Config file

TOML, read with the standard library (`tomllib`). Resolution order, first match wins:

1. `--config PATH`
2. `$DECK_BUILDER_CONFIG`
3. The first `deck-builder.toml` found walking up from the current directory
4. `~/.config/deck-builder/config.toml`
5. Built-in defaults

```toml
# deck-builder.toml - written by `deck-builder init`; gitignored in this repo
workspace = "workspace"                  # relative to this file
brand_paths = ["workspace/brands", "~/clients/acme-brand-kit"]
default_brand = "neutral"

[render]
backend = "auto"                         # auto | powerpoint | libreoffice
dpi = 96
contact_batch = 20                       # slides per contact sheet
```

Relative paths resolve against the config file's directory. `~` expands.

### 4.2 Workspace layout

```
workspace/
  brands/<slug>/          # brand kits created here by onboarding
  decks/<slug>/           # deck.md or deck.xlsx, plus assets/
  out/                    # built files, manifests, renders
  .cache/                 # derived assets (recolored icons), keyed by content hash
```

`deck-builder init` creates the workspace, writes `deck-builder.toml`, and generates the neutral example brand into `workspace/brands/neutral/`.

**R-4.1** `init` is idempotent: a second run changes nothing and reports that. AC: running `init` twice leaves every file's hash unchanged.
**R-4.2** `.gitignore` is an allowlist: `/*` ignores everything, and only the shipped top-level files and folders are re-included. `workspace/` ships holding only its README, and `.claude/` ships only `skills/` and `agents/`. Everything user-, workspace- or project-specific (config, brands, decks, output, cache, local Claude settings) is written to ignored paths. AC: `git status` is clean after onboarding, and `git check-ignore` matches `deck-builder.toml`, `workspace/brands/x` and `.claude/settings.local.json`.

## 5. Brand kits

### 5.1 Contents

```
<slug>/
  brand.yaml        # brand standards: identity, palette, fonts, logos, icons, voice, lint
  tokens.yaml       # template contract: layouts, fields, placeholders, budgets, chart and table styling
  template.potx     # the design: masters, layouts, theme, placeholders (.pptx also accepted)
  assets/           # logos, icons
  fonts/            # optional; never committed when the font license forbids it
```

`brand.yaml` is what a person decides. `tokens.yaml` is the machine contract between the template and the content, generated by `brand init` or `inspect` and then tuned.

### 5.2 brand.yaml

```yaml
spec_version: 1
name: Pemberton Paper Co.        # display name
slug: pemberton                  # folder name; decks call the brand by this
version: 1.0.0                   # bump on any change that affects output
description: Regional paper supplier, sales and ops decks

palette:                         # named colors, hex without '#'
  primary: "1F3A5F"
  accent: "E07A2F"
  ink: "1B1B1B"
  muted: "6B7280"
  surface: "F4F5F7"
  background: "FFFFFF"

theme_colors:                    # OOXML theme slots -> palette names (used by brand init)
  dk1: ink
  lt1: background
  dk2: primary
  lt2: surface
  accent1: primary
  accent2: accent
  accent3: muted
  accent4: "9DB4C0"              # a hex value is allowed anywhere a palette name is
  accent5: "C8553D"
  accent6: "5B8C5A"
  hlink: accent
  folHlink: muted

fonts:
  heading: {family: Inter, fallback: Arial}
  body: {family: Inter, fallback: Arial}

logos:                           # id -> file in assets/
  primary: assets/logo.png
  mono: assets/logo-mono.png

icons:
  dir: assets/icons              # PNG alpha masks; file stem is the icon id
  default_color: primary
  source: "Lucide, ISC license"  # recorded in the asset inventory

voice:                           # read by the LLM; not enforced
  - One idea per slide. The title states the takeaway.
lint:                            # enforced by check
  max_slides: 40
  banned_patterns: ["—", "(?i)\\bsynerg"]

generate:                        # read only by brand init
  slide_size: "16:9"             # 16:9 | 4:3
  layout_set: standard           # minimal | standard | full
  logo_on_master: primary        # logo id, or omit
```

**R-5.1** `brand.yaml` and `tokens.yaml` validate against JSON Schemas shipped in the package (`deck-builder schema brand|tokens`). A schema error exits 2 with every violation listed. AC: a fixture with three schema errors reports all three.

### 5.3 tokens.yaml

As in the prototype, with these changes: `voice` and `lint` move to `brand.yaml`; colors in `chart` and `table` may be palette names; a new field kind `icon`.

```yaml
spec_version: 1
chart:
  font_size: 12
  text_color: ink
  gridline_color: "E5E7EB"
  colors: [primary, accent, muted]
table:
  font_size: 14
  header_fill: primary
  header_text: background
  band_fill: surface
layouts:
  content:
    template_layout: "Content"
    master: null                 # set when several masters reuse a layout name
    heading_field: title
    fields:
      title: {idx: 0, kind: text, max_chars: 70, required: true}
      body:  {idx: 1, kind: bullets, max_chars: 420, max_bullets: 6, max_bullet_chars: 110, max_level: 1}
  feature:
    template_layout: "Icon Row"
    fields:
      title: {idx: 0, kind: text, max_chars: 60, required: true}
      icon1: {idx: 10, kind: icon, color: accent}
      text1: {idx: 11, kind: text, max_chars: 90}
```

Field kinds: `text`, `bullets`, `table`, `chart`, `image`, `icon`. Chart and table fonts come from the template theme unless `font` is set.

### 5.4 Registry: durable, discoverable, callable

A brand is any directory under a `brand_paths` entry that contains a `brand.yaml`. The registry is computed on each run; there is no database.

| Command | Does |
|---|---|
| `brand list [--json]` | Every brand found: slug, name, version, path, valid or not |
| `brand show <slug> [--json]` | The compact contract: layouts, their fields, kinds and budgets, palette names, logo and icon ids. This is what the LLM reads before writing a deck. |
| `brand check <slug> [--json]` | Schemas valid; every `template_layout` exists in the template; every field `idx` exists on its layout; every logo and icon file exists |
| `brand init <slug> --from brand.yaml` | Generates `template.potx`, `tokens.yaml` and recolored assets from `brand.yaml` ([section 5.5](#55-brand-generation)) |
| `brand adopt <slug> --template FILE` | Wraps an existing template: copies it in, writes a starter `tokens.yaml` from `inspect`, and a `brand.yaml` skeleton with the template's theme colors and fonts filled in |

A deck calls a brand by slug (`brand: pemberton` in front matter, or the `deck` sheet in a workbook). Explicit `template:` and `tokens:` paths still work and override the brand.

**R-5.2** Duplicate slugs across `brand_paths` are an error (`BRAND_DUPLICATE`) naming both paths. AC: fixture with two `neutral` kits fails with both paths in the message.
**R-5.3** `brand show --json` for the neutral brand is under 4 KB. AC: size asserted in a test.

### 5.5 Brand generation

`brand init` is deterministic: the same `brand.yaml` and engine version give a byte-identical kit.

- Starts from python-pptx's bundled default template, sets the slide size from `generate.slide_size`, and replaces its 11 stock 4:3 layouts with the chosen layout set, placed on a 12-column grid with fixed margins.
- Writes `theme_colors` into the theme's color scheme and `fonts` into its font scheme, so every placeholder inherits them.
- Places the logo on the master if `logo_on_master` is set.
- Clears python-pptx's default document properties (its description and last-modified-by values).
- Writes `tokens.yaml` with budgets estimated from placeholder size and font size, marked `# estimated` for tuning after a test render.
- Copies the logos and icons `brand.yaml` names into the kit. Icons are PNG alpha masks, recolored at build time to the field's `color` or `icons.default_color` and cached by content hash. SVG icons are out of scope for v0.1.0; `check` rejects them with `ASSET_FORMAT`.

| Layout set | Layouts |
|---|---|
| minimal | title, section, content, closing |
| standard | minimal plus two-col, big-number, chart, table, image, quote |
| full | standard plus image-right, icon-row, comparison, agenda, team |

**R-5.4** A generated kit passes `brand check` and builds every example deck. AC: test over all three layout sets.
**R-5.5** A generated template opens in LibreOffice without error (render test) and in PowerPoint for Mac without a repair prompt (manual release check).

## 6. Assets: inventory, references, mapping

### 6.1 Classes

| Class | Declared in | Referenced as |
|---|---|---|
| Palette color | `brand.yaml` `palette` | A name (`primary`) in tokens, chart blocks, `color:` options |
| Font | `brand.yaml` `fonts` | Theme only; never referenced from a deck |
| Logo | `brand.yaml` `logos` | `brand:logo/<id>` |
| Icon | `brand.yaml` `icons.dir` | `brand:icon/<id>` |
| Deck image | Files under the deck's `assets/` | A relative path, `assets/chart-export.png` |
| Layout and field | `tokens.yaml` | `layout: <name>` and field names in the deck |
| Placeholder | The template | `idx` in `tokens.yaml` only; decks never name an `idx` |

### 6.2 Inventory

`deck-builder assets <brand-slug | deck-file> [--json]` lists every asset: id, class, path, SHA-256, pixel size for images, and source or license where declared. For a deck it also lists which slides use each asset.

### 6.3 Resolution

`check` resolves every reference before anything is built:

- An unknown logo, icon or palette name raises `UNKNOWN_ASSET`.
- An image in an unsupported format raises `ASSET_FORMAT`. Supported: PNG, JPEG, GIF, BMP, TIFF. SVG is rejected with a hint to convert it.
- An image smaller than its placeholder at 150 DPI raises the warning `ASSET_LOW_RES`.

### 6.4 Mapping into the deliverable

The build writes `<deck>.manifest.json` beside the PPTX: for each slide, its logical layout, template layout, and each field with its placeholder `idx`, value kind, character count, the shape name of a text field (so the render step can name the field that overflowed) and any asset id with its hash; plus the brand slug, version and template hash, the engine version, the input file's hash, and the deck's content hash. The content hash is the SHA-256 of the deck's canonical markdown, so it's the same whichever format the deck was written in. The manifest is deterministic and is what agents read instead of opening the PPTX. The PPTX custom properties hold `deck-builder:engine`, `deck-builder:brand`, `deck-builder:brand-version`, `deck-builder:template-sha256` and `deck-builder:content-sha256`; the input file's own hash stays out of the PPTX, so one deck builds the same file from `.md`, `.xlsx` or `.csv`.

Derived assets (recolored icons) are cached in `workspace/.cache/assets/<sha256>.png`, keyed by source content and color.

**R-6.1** Every asset embedded in a PPTX appears in its manifest with a matching hash. AC: a test cross-checks manifest hashes against the media parts in the zip.

## 7. Inputs

All three formats parse into the same model: a deck (metadata) holding an ordered list of slides, each with a layout, fields and notes.

### 7.1 deck.md

As the prototype's `references/spec-format.md`, plus:

- `spec_version: 1` and `brand: <slug>` in front matter. The engine refuses a newer `spec_version` (`SPEC_VERSION`).
- Inline markup: `**bold**`, `*italic*`, `` `code` ``, `[text](url)` hyperlinks. Anything else is literal text.
- Asset references per [section 6](#6-assets-inventory-references-mapping).
- `date:` in front matter sets the document's created and modified dates; default `2000-01-01`.

### 7.2 Workbook (.xlsx)

| Sheet | Holds |
|---|---|
| `deck` | Two columns, `key` and `value`: the front matter |
| `slides` | One row per slide. Columns: `slide` (number, informational), `layout`, `title`, one column per field name, `notes`. Columns whose header starts with `#` are helpers and ignored. |
| `chart-NN-<field>` | One chart: option rows (`type`, `number_format`, `labels`, `legend`, `title`, `colors`), a blank row, then a grid with categories down the first column and one series per column. Excel forbids `:` in sheet names, so the kind is a prefix. |
| `table-NN-<field>` | One table: header row, then data rows |
| `_lists` | Hidden; the layout dropdown's values and each layout field's character budget, for the live counts |
| `README` | Instructions for people; ignored |

In `slides`, a cell value `sheet:<id>` places that chart or table. Bullets are lines starting `- `, two spaces per nesting level. Cells are read as values only, so re-saving in Excel, SharePoint or LibreOffice doesn't change the result.

### 7.3 CSV

The `slides` sheet alone. `sheet:` references are an error (`CSV_NO_SHEETS`).

### 7.4 Bulk

A `deck.md` or workbook with `{{column}}` tokens plus `--data rows.csv|.xlsx` builds one deck per row. Unknown tokens raise `UNKNOWN_TOKEN`. `--name` sets the file name pattern.

## 8. convert

`deck-builder convert <in> <out>`, format chosen by extension: `.md`, `.xlsx`, `.csv`.

- **Lossless contract.** For any valid input `X`: `parse(convert(X))` equals `parse(X)` after dropping source positions, and both build to byte-identical PPTX files. A conversion that would drop content (charts or tables to CSV) fails with `CONVERT_LOSSY` and writes nothing.
- **Canonical writers.** Markdown and workbook output have one canonical form, so a second round trip changes nothing byte-for-byte.
- **Team-ready workbook.** When the brand resolves, the `layout` column gets a dropdown of the brand's layouts, the header row is frozen, every budgeted field gets a `#chars:<field>` helper column with a `LEN` formula and red conditional formatting over budget, and a `README` sheet explains the format.

The supported team path is: write `deck.md`, `convert` to `deck.xlsx`, share it for editing, `build deck.xlsx`. Converting back to markdown works at any point.

**R-8.1** Round trip holds for every example deck, and one deck builds the same file from any format. AC: tests convert md to xlsx to md and md to xlsx to md to xlsx, asserting model equality, byte-stable canonical forms on the second pass, and byte-identical PPTX files from the `.md`, the `.xlsx` and the converted-back `.md`. `convert` itself parses its output back and refuses with `CONVERT_LOSSY` if anything changed.
**R-8.2** A workbook edited and re-saved by LibreOffice still builds identically. AC: render-tier test re-saves through `soffice --convert-to xlsx` and rebuilds.

## 9. CLI

```
deck-builder init [--dir D]                         # workspace, config, neutral brand, example decks
deck-builder doctor [--powerpoint] [--json]         # deps, tools, render backends; --powerpoint tests automation
deck-builder brand list|show|check|init|adopt ...   # section 5.4; init and adopt take --out and --force
deck-builder inspect <template> [--yaml|--json]     # layouts, placeholders, theme
deck-builder assets <brand|deck> [--json]           # section 6.2
deck-builder check <deck> [--render] [--json]       # validate; --render also builds to the default output, renders, measures
deck-builder build <deck> [-o OUT] [--data ROWS --name PATTERN] [--json]
deck-builder convert <in> <out> [--force] [--json]  # never overwrites without --force
deck-builder render <pptx> [--backend B] [--slides 3,7] [--dpi N] [--json]
deck-builder schema brand|tokens|manifest
deck-builder docs [topic]                           # reference topics shipped with the engine
deck-builder explain <CODE>                         # cause and fix for one issue code
deck-builder skills install [--target ~/.claude] [--yes]
deck-builder --version
```

Format references (`deck-md`, `workbook`, `brand-yaml`, `tokens-yaml`, `workflow`, `codes`) ship inside the package and print through `docs`, so they always match the installed engine. Skills point at these topics instead of copying them, which keeps skills small and in sync.

### 9.1 Output

- Exit `0` success, `1` validation issues, `2` usage or environment errors.
- Human output is terse: one summary line on success, one line per issue: `error BUDGET_CHARS deck.md:23 slide 4 body: 433 chars, budget 420`.
- `--json` prints one object: `ok`, `command`, `input`, `output`, `slides`, `issues[]` (`severity`, `code`, `file`, `line`, `slide`, `field`, `message`, `actual`, `limit`), plus command-specific keys (`backend`, `render_dir`, `slide_png`, `flagged_slides` as `{slide, codes}`, `contact_sheets`, `manifest`, `content_sha256`). An environment error (exit 2) puts `error` and, where one applies, `code` in the object.
- All issues are collected before exiting.

### 9.2 Issue codes

A stable, documented enum. Skills key fixes off codes, never off message text.

`PARSE`, `SPEC_VERSION`, `SCHEMA`, `UNKNOWN_BRAND`, `BRAND_DUPLICATE`, `BRAND_INVALID`, `TEMPLATE_MISMATCH`, `UNKNOWN_LAYOUT`, `UNKNOWN_FIELD`, `MISSING_FIELD`, `KIND_MISMATCH`, `BUDGET_CHARS`, `BUDGET_BULLETS`, `BUDGET_BULLET_CHARS`, `BUDGET_LEVEL`, `TABLE_SHAPE`, `CHART_SHAPE`, `UNKNOWN_ASSET`, `ASSET_FORMAT`, `ASSET_LOW_RES`, `MISSING_IMAGE`, `BANNED_PATTERN`, `MAX_SLIDES`, `UNKNOWN_TOKEN`, `CSV_NO_SHEETS`, `CONVERT_LOSSY`, `OVERFLOW_MEASURED`, `EMPTY_PLACEHOLDER`, `MISSING_FONT`, `OFFICE_REPAIR`, `RENDER_UNVERIFIED`, `SKILL_CONFLICT`. `ASSET_LOW_RES`, `MISSING_FONT`, `RENDER_UNVERIFIED` and `SKILL_CONFLICT` are warnings; the rest are errors.

**R-9.1** Every code's cause and fix live in one table in the engine (`errors.CODES`). `docs/issue-codes.md` is generated from it by `deck-builder docs codes`, and every code is exercised by at least one test. AC: a test compares the committed file with fresh output, and a test asserts each code appears in a test file.

### 9.3 skills install

Links the repo's skills and agent into another Claude Code setup so decks can be built from other repos. Prints every link it would create and changes nothing without `--yes`. Never overwrites an existing file; reports a conflict instead.

## 10. Build pipeline

```
parse -> resolve brand, template, assets -> validate -> (check stops here) -> fill placeholders -> normalize -> save -> manifest
```

- Rendering code reads placeholder geometry and tokens only. No hardcoded positions, fonts or colors in engine code outside documented defaults; a lint test rejects literal `RGBColor(` and `Pt(` outside the token readers.
- Template sample slides are removed unless `--keep-template-slides`.
- Unused placeholders on a built slide are removed, so no "Click to add text" boxes remain.

### 10.1 Determinism

python-pptx output isn't byte-stable on its own: zip entry timestamps and the chart workbooks it embeds through XlsxWriter record the current time (verified 2026-10-01 against python-pptx 1.0.2). The engine normalizes on save:

- Every zip entry, outer and in each embedded workbook, gets the timestamp 1980-01-01 00:00:00, a fixed entry order, and fixed compression.
- Core properties: `created` and `modified` from front matter `date`, `lastModifiedBy` and `creator` from `author` or empty, `description` empty, `revision` 1.
- The embedded workbook's own properties get the same treatment.

**R-10.1** Building the same input twice, at different times, gives identical SHA-256. AC: a test builds twice more than two seconds apart, past the zip timestamp resolution. Byte equality holds on one machine; across machines a different zlib can change compressed bytes, which is why the manifest also records `content_sha256` over the uncompressed parts.

## 11. Text fit

python-pptx can't measure rendered text. Three layers, cheapest first:

1. **Budgets.** Characters, bullets, bullet length and nesting per field. Always on.
2. **Measured.** After rendering, `pdftotext -bbox-layout` gives every word's position. Each word is assigned to the nearest text shape whose text contains it, words inside charts and tables are left out, and any assigned word more than 3 pt outside its shape raises `OVERFLOW_MEASURED` with the overrun in points and the field name from the manifest. Exact on PowerPoint's PDF; a close proxy on LibreOffice's. The assignment is a heuristic: text that overflows into a neighboring shape containing the same words can go unreported.
3. **Font metrics.** Pre-render wrapping with Pillow and the brand font files. Deferred past v0.1.0.

Autofit stays off in generated templates.

## 12. Rendering and QA

| Backend | When | Fidelity |
|---|---|---|
| `powerpoint` | macOS with `/Applications/Microsoft PowerPoint.app`, a logged-in session | Exact: real fonts, real layout |
| `libreoffice` | Otherwise, including CI | Close; fonts can substitute and spacing drifts |

`--backend auto` (default) prefers PowerPoint, then LibreOffice, else exits 2 with an install hint. The JSON result names the backend that ran.

Output: `<deck>.render/` with `deck.pdf`, `slide-NN.png` and `contact-NN.png` (one per `contact_batch` slides). Slide PNGs are sized from the slide dimensions times `dpi` (1280x720 for 16:9 at 96), not from the PDF page, whose size can differ by a fraction of a point between renderers.

### 12.1 Flagged slides

`render --json` and `check --render --json` return `flagged_slides`: slides with `OVERFLOW_MEASURED`, `EMPTY_PLACEHOLDER` or `ASSET_LOW_RES`, each with its codes. `MISSING_FONT` is reported for the deck, not per slide. Agents open PNGs for flagged slides only, plus contact sheets, where flagged slides have a red frame. At the default 1280x720, one slide image costs about 1,200 tokens; a contact sheet of 20 thumbnails is about one megapixel and costs about the same.

### 12.2 PowerPoint backend (macOS)

AppleScript via `osascript`; no extra Python dependencies.

1. Copy the deck into `~/Library/Containers/com.microsoft.Powerpoint/Data/deck-builder/`. Writing elsewhere can raise a file-access dialog that blocks an unattended run.
2. Open it, save as PDF in the same folder, close that presentation without saving.
3. Copy the PDF out and rasterize with `pdftoppm`.
4. Quit PowerPoint only if this run launched it. Never touch presentations that were already open.

- One render at a time, enforced by a lock file in the container folder.
- Timeout 180 s per deck; on timeout, report and leave PowerPoint running.
- Automation permission: a denial (osascript error -1743) exits 2 with the System Settings path to grant it. `doctor --powerpoint` checks it; plain `doctor` doesn't, because the check launches PowerPoint.
- Until `probe_powerpoint.sh` has passed on a real Mac, every PowerPoint-backed result includes the warning `RENDER_UNVERIFIED`.

### 12.3 LibreOffice backend

Headless, with a throwaway user profile per run and a 300 s timeout. Only renders files the engine built; documented as unsafe for third-party decks.

### 12.4 Font check

`pdffonts` on the rendered PDF compares embedded fonts with `brand.yaml` fonts. A font rendered with its declared fallback, or with something else, raises the warning `MISSING_FONT`. LibreOffice can render a template's theme font with its own default even when the font is installed, so the warning is a fidelity note under LibreOffice and a real substitution under PowerPoint.

## 13. Claude Code layer

### 13.1 CLAUDE.md

Short. States the division of labor, that all deck work goes through the CLI, and the onboarding trigger: if no `deck-builder.toml` resolves, run the `deck-onboard` skill before anything else.

### 13.2 Skills

| Skill | Type | Job |
|---|---|---|
| `deck-builder` | Deterministic | How to run the CLI: the command sequence, reading `--json`, fixing by issue code, the review gate. About 100 lines; formats and codes live in `references/` and load on demand. |
| `deck-brand` | Freeform | Builds `brand.yaml` with the user from a brand guide, website colors or an existing deck; chooses a layout set; sources icons with their licenses; runs `brand init` or `brand adopt`; tunes budgets from a test render; walks the user through polishing the template in PowerPoint. |
| `deck-onboard` | Freeform | Runs `doctor`, explains and offers fixes for anything missing, runs `init`, then the brand branch (section 14), then a first build and render. |

Skills never contain engine logic. A skill that needs a new capability proposes a CLI change.

### 13.3 deck-builder-agent

`.claude/agents/deck-builder-agent.md`, `model: sonnet`. Tools: Bash, Read, Edit, Write, Glob, Grep. It runs the write, check, fix, build, render loop in its own context, stops after three fix loops, and returns a short report: output path, manifest path, slide count, remaining issues by code, flagged slides, and anything it assumed.

### 13.4 Review gate

The main agent approves all subagent work before it reaches the user:

1. Runs `deck-builder check <deck> --json` itself and confirms zero errors.
2. Reads the manifest and the subagent's report.
3. Opens the flagged slide PNGs and the contact sheets.
4. Approves, or sends the subagent back with fixes named by slide and code.

### 13.5 Token budget

- The engine does all deterministic work, so the LLM spends tokens on content and review only.
- Terse CLI output; `--json` only when parsing.
- `brand show` instead of reading `tokens.yaml`; the manifest instead of opening the PPTX.
- Flagged slides and contact sheets only, never every slide by default.
- Build loops run in the subagent's context.

### 13.6 Other models

Nothing in the engine assumes Claude. Any agent that can run a shell command and read JSON can drive the CLI, including a local model. Supporting one is future work ([section 20](#20-open-decisions)).

## 14. Onboarding

Triggered by `CLAUDE.md` on first use, or by asking for it.

1. `deck-builder doctor`: Python dependencies, poppler, LibreOffice, PowerPoint and its automation permission. Offers the install command for anything missing and waits for the user.
2. `deck-builder init`.
3. Brand branch, the user's choice:
   - **Skip:** use the neutral example brand.
   - **Bring your own:** `brand adopt` around an existing `.potx` or `.pptx`; the LLM fills in `brand.yaml` with the user.
   - **Starter:** a minimal `brand.yaml` (palette, fonts, logo) and `brand init` with the standard layout set. Improve later.
   - **Full:** the `deck-brand` skill works through palette, theme slots, fonts, logos, icons, layout set, voice and lint with the user, then `brand init`, then polishing in PowerPoint.
4. A first deck from an example, `build`, `render`, and a look at the contact sheet together.
5. Optional: `skills install` for use from other repos.

**R-14.1** Onboarding finishes on a machine with only LibreOffice and poppler installed. AC: manual run recorded in `docs/release-checklist.md`; CI covers steps 1 to 4 without the LLM.

## 15. Repo layout

```
deck-builder/
  pyproject.toml  uv.lock  README.md  SPEC.md  LICENSE  CHANGELOG.md  CLAUDE.md
  .gitignore  .github/workflows/ci.yml
  src/deck_builder/
    __init__.py  __main__.py  cli.py  commands.py  config.py  errors.py  model.py  pipeline.py
    docs.py  template.py  validate.py  assets.py
    brand/      registry.py  schema.py  kit.py  inspect.py  layouts.py  generate.py
    parse/      markdown.py  csvfile.py  workbook.py
    write/      markdown.py  workbook.py           # canonical writers for convert
    build/      deck.py  text.py  visuals.py  normalize.py
    qa/         backends/{powerpoint.py,libreoffice.py}  rasterize.py  measure.py  fonts.py  contact.py
    doctor.py
    schemas/    brand.schema.json  tokens.schema.json  manifest.schema.json
    reference/  *.md                               # topics printed by `deck-builder docs`
    data/       brands/neutral/  decks/quarterly-review/  decks/bulk-outreach/
  .claude/
    skills/deck-builder/  skills/deck-brand/  skills/deck-onboard/
    agents/deck-builder-agent.md
  workspace/README.md                              # placeholder; everything else here is ignored
  scripts/probe_powerpoint.sh  scripts/make_example_assets.py
  docs/issue-codes.md  docs/release-checklist.md
  tests/unit/  tests/render/
```

The neutral brand and the example decks ship inside the package (`data/`), so `init` works from any install, including `uv tool install`. Layout sets are defined in `brand/layouts.py`.

## 16. Dependencies

| Package | License | Use |
|---|---|---|
| python-pptx 1.0.x | MIT | PPTX read and write. Brings lxml (BSD-3), Pillow (MIT-CMU), XlsxWriter (BSD-2). Last release 1.0.2, Aug 2024. |
| PyYAML | MIT | `safe_load` only |
| openpyxl | MIT | Workbook read and write; core, since `convert` is core |
| defusedxml | PSF | Hardened XML parsing for workbooks from outside the org |
| jsonschema | MIT | Schema validation |

Dev: pytest, ruff, mypy, pip-audit. Python 3.11 or later, managed with uv, built with hatchling. Direct dependencies pinned with upper bounds and locked in `uv.lock`.

System tools: poppler (GPL, invoked as a CLI) for rendering and measurement; LibreOffice (MPL-2.0) when PowerPoint isn't present. `build`, `check`, `convert`, `inspect`, `brand` and `assets` need none of them.

## 17. Testing

- **Unit** (`tests/unit`): parsers, writers, validation, every issue code, config resolution, registry, bulk substitution, generation of all three layout sets, `init` idempotence, and the PowerPoint backend's failure paths with `osascript` simulated.
- **Determinism:** rebuilds are byte-identical (R-10.1), generated kits are byte-identical, and one deck builds the same file from any format (R-8.1). Committed golden snapshots are deferred, because compressed bytes can differ across zlib versions; see [section 20](#20-open-decisions).
- **Round trip:** R-8.1 for every example deck.
- **Validity:** every built file reopens in python-pptx.
- **Render** (`tests/render`, marked `render`, skipped without LibreOffice and poppler): the example deck renders with no flags, measured overflow on a deliberately long slide, selected-slide renders, the unverified PowerPoint marking, and R-8.2.
- **Office** (marked `office`): the PowerPoint backend on a real Mac, run by hand before each release (`docs/release-checklist.md`).
- **Static** (`tests/unit/test_static.py`): no engine module imports a network library, `RGBColor(`/`Pt(` appear only in the token reader (with a positive control), `yaml.safe_load` only. Plus ruff and mypy.

## 18. CI

GitHub Actions on every push and pull request, Ubuntu:

| Job | Runs | Enforces |
|---|---|---|
| lint | ruff, mypy | Code quality and types |
| test | unit, determinism, round trip, validity, static rules | Determinism, lossless convert, no network imports |
| audit | `pip-audit` on the locked runtime dependencies, exported from `uv.lock` | No dependencies with known CVEs |
| render | Installs `libreoffice-impress`, `poppler-utils` and `fonts-liberation`, runs the render tier | The render path works on a clean machine |

The Office tier never runs in CI.

## 19. Security and supply chain

- No network access at runtime; no telemetry.
- `yaml.safe_load` only; `defusedxml` installed; Pillow decodes images, so images from outside the org are treated as untrusted.
- The renderers only open files the engine built.
- `skills install` never overwrites and changes nothing without `--yes`.
- Font files are never committed when their license forbids redistribution; `workspace/` is gitignored.
- Dependabot for dependency updates; `pip-audit` blocks CI on known CVEs.

## 20. Open decisions

| Decision | Default | Decider |
|---|---|---|
| Bundle a starter icon subset (Lucide, ISC) in the package | No; the user supplies icons, and the neutral brand ships six drawn for the repo | Repo owner |
| SVG icons, converted with `rsvg-convert` | Not in v0.1.0; PNG alpha masks only | Repo owner |
| Committed golden snapshots compared on content hash (uncompressed parts) rather than file bytes | Not in v0.1.0; determinism is tested by rebuilding | Repo owner |
| Slide numbers and footers on generated layouts (python-pptx doesn't copy those placeholders to slides) | Not in v0.1.0 | Repo owner |
| Diagrams from text (Graphviz or Mermaid) rendered into image placeholders | Not in v0.1.0 | Repo owner |
| Support for a local model driving the CLI | Future work; the CLI already allows it | Repo owner |
| Publish to PyPI | No; install from a pinned git tag | Repo owner |
| Make the repo public | After v0.1.0 and a check that no client material is in history | Repo owner |

## 21. Milestones

| Version | Scope |
|---|---|
| 0.1.0 | Everything in sections 4 to 19 except the deferred items below |
| 0.2.0 | Font-metric overflow (section 11, layer 3), starter icon set if approved, diagrams if approved |
| later | Local-model support, PyPI |

## 22. Migration from the prototype

1. Port `build.py` into `parse/`, `validate.py` and `build/` with no behavior change; a parity test compares prototype and package output on the prototype's examples (slide XML, ignoring normalization).
2. Move `inspect_template.py` and `render.py` behind `cli.py`.
3. Move `tokens.example.yaml` fields into `brand.yaml` and `tokens.yaml` per sections 5.2 and 5.3.
4. Move the prototype's `references/` into the `deck-builder` skill and rewrite `SKILL.md` to call the CLI.
5. Delete `deck-builder-skill/` and `deck-builder-SPEC.md` once 0.1.0 passes its tests.
