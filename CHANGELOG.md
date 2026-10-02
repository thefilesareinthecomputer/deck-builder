# Changelog

## Unreleased

### Added

- Slide numbers and an optional footer, kept minimal: a 10 pt muted number at the bottom left of content slides, on the logo's line, and `footer: <text>` in front matter for a short text after it. No date, no boxes. `slide_numbers: false` turns numbers off for a deck, `generate.slide_numbers: false` for a brand. Adopted templates' own slide-number placeholders now appear on slides. `brand show`, `check` and `build` report them.
- `deck-builder mcp`: the engine as MCP tools over stdio (hand-written JSON-RPC, no new dependency), for agents without a shell. Each tool runs the CLI's own parser and handler and returns its `--json` object; every path is confined to the workspace, brand writes to a `brand_paths` folder. `doctor` reports whether it answers.
- `brand add-asset <slug> <png> --as logo/<id>|icon/<id>` copies a PNG into a kit.
- `import <deck.pptx> <out> --brand <slug> | --adopt <new-slug>`: an existing deck back into `deck.md`, its images (named by slide and content hash) and `import-report.md`. Layouts map by name or by best fit on placeholder types; placeholders map to fields; runs become inline markup, tables pipe tables, charts chart blocks, notes `Notes:`; brand logos and icons are recognized by hash. Content that can't be placed goes to the slide's notes and the report, SmartArt, media, embedded objects and groups are reported, linked images are never fetched, and local formatting is dropped and counted. The `deck-builder` skill has a "Refresh an existing deck" path.
- `check` and `build` accept a deck folder and use its `deck.md`, `deck.xlsx` or `deck.csv`, in that order.
- `build -o` accepts a folder (an existing one, or a path ending in `/`) and writes the default file name inside it.
- `brand check`, `brand init` and `brand adopt` warn with the new `LOW_CONTRAST` code when a color pair misses WCAG 2.2 contrast: 4.5:1 for ink on background and on surface, background on primary, and links on background; 3:1 for the icon color and chart series colors on background.
- Charts and tables have alt text that names the chart type, title, series and categories, or the table's columns and row count.
- Human output ends with one `for the fix: deck-builder explain <CODE>` line naming every error code in the result.
- Help text on the `deck`, `-o`, `input`, `output` and `pptx` arguments.
- `tests/fixtures/demo-brands/`: three fictional brands and a showcase deck that bulk-builds into all three; unit and render tests build and render it.
- README rewritten around a three-brand showcase; `scripts/readme_images.py` regenerates its images.
- AGENTS.md holds the agent instructions; CLAUDE.md imports it.

### Security

- A deck image must resolve, symlinks followed, inside the deck's folder, and a brand asset inside its kit; anything else is the new error `ASSET_OUTSIDE`, in every mode and per bulk row. Logo and icon ids containing `/`, `\` or `..` are `UNKNOWN_ASSET`. Image messages name the reference as written, not the resolved path. The manifest records each image's source file.
- Front matter `output:` must be a `.pptx` inside the deck's folder or `<workspace>/out/`; `-o` takes a `.pptx` path or a folder; a build never replaces an existing file that has no manifest beside it.
- Bulk data values with a line break, or that would start a heading or image line, are the new error `BAD_DATA_VALUE` for that row.
- A template's theme XML is parsed with entities, DTDs and network loads off, so an adopted template or imported deck can't read local files through XML entities; such a theme is refused.
- Re-rendering deletes only the files render writes, not the whole `.render/` folder.
- The showcase fixture's hero images moved into `showcase/assets/`, since a deck's images must sit inside its folder.
- `deck-builder-agent` and `deck-brand-agent` have no shell: Bash is removed and they reach the engine only through the deck-builder MCP server, confined to the workspace, so a missing or failing server leaves them able to run nothing. `skills install` refuses until `deck-builder` is on PATH. Approved by the user.
- Front matter `template:` and `tokens:` must be files inside the deck's folder.
- `deck-decomposer-agent` runs no commands: Bash is removed, since it reads untrusted material. The main agent puts `brand show <slug> --json` and `docs deck-md` in its prompt and runs `check` on its draft.

### Changed

- Canonical `deck.md` front matter (from `convert` and `import`) is one `key: value` per line instead of a single YAML flow mapping. Content hashes change once as a result.
- The neutral brand passes its own contrast check: links use `primary` (10.95:1, was 4.10:1) and the fourth chart color is `5B8FC7` (3.39:1, was `8FB3D9` at 2.18:1).

### Fixed

- `build deck.md` run inside the deck's own folder names the output after that folder instead of writing `out/.pptx`.
- LibreOffice renders on macOS see the system's fonts. Headless LibreOffice saw only its bundled fonts, so brand fonts such as Georgia rendered as substitutes and `MISSING_FONT` and overflow measurements were wrong.
- Overflow measurement allows for the ascent and descent of tall-metric fonts such as Avenir Next, which flagged one-line titles and big numbers that fit.
- Table rows without a `row_fill` or `band_fill` token have no fill. The default table style's accent tint and banding showed through as gray rows.
- A heading line inside a slide that isn't a field heading, such as `### Some words` or `# Note`, is a `PARSE` error instead of becoming a bullet.
- A web address as an image gets a `MISSING_IMAGE` message that says to download it into the deck folder.
- `UNKNOWN_BRAND` says to run `deck-builder init` or pass `--config` when no `deck-builder.toml` was found.
- `render` given a deck or a folder points at `check --render`, and rejects other non-`.pptx` files, instead of a traceback.
- `init --dir` creates the folder when it doesn't exist, instead of a traceback.

### Docs

- `docs deck-md`: quoting a field value that contains `: `, stray headings, and local images only.
- `deck-onboard` step 2: working in a folder outside the clone with `init --dir` and `uv run --project`.
- `MISSING_FONT` means the font isn't installed where the deck rendered. The code text, SPEC and the `deck-brand` and `deck-builder` skills no longer describe it as LibreOffice ignoring a theme font; that was the macOS font-visibility bug fixed above.

## 0.1.0

First release.

- Inputs: `deck.md`, `deck.xlsx` and `slides.csv` parse into one slide model; bulk mode builds one deck per data row.
- `check`: budgets, field kinds, layouts, assets, lint rules and tables and charts, reported with stable issue codes.
- `build`: placeholders filled with inline markup, native charts and tables, logos and recolored icons; byte-identical rebuilds; one deck builds the same file from any input format; a manifest per build.
- `convert`: lossless markdown, workbook and CSV conversion, checked by parsing the output back before writing it. Workbooks have a layout dropdown, live character counts and a README sheet.
- Brands: registry by slug, JSON Schemas, `brand show`, `brand check`, `brand adopt` for existing templates, and `brand init`, which generates a 16:9 template and `tokens.yaml` from `brand.yaml` with minimal, standard or full layout sets.
- `render`: LibreOffice backend, PowerPoint for Mac backend (unverified), exact-size slide PNGs, contact sheets, measured overflow, empty-placeholder and font checks, flagged slides; `check --render` in one step.
- `init`, `doctor`, `assets`, `inspect`, `docs`, `explain`, `schema`, `skills install`.
- Claude Code layer: `deck-onboard`, `deck-brand` and `deck-builder` skills and the `deck-builder-agent` subagent.
