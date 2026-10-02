# Changelog

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
