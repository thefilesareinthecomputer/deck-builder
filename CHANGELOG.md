# Changelog

All notable changes to this project are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

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

- CI runs lint, type checks, tests, a dependency audit and the render tier on every push and weekly. Dependabot keeps the lockfile and the Actions current.
- Three fictional demo brands and a showcase deck in `tests/fixtures/demo-brands/`; `scripts/readme_images.py` regenerates the README images from them.
