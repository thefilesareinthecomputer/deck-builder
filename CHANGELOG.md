# Changelog

## Unreleased

### Added

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
- Re-rendering deletes only the files render writes, not the whole `.render/` folder.
- The showcase fixture's hero images moved into `showcase/assets/`, since a deck's images must sit inside its folder.

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
