# deck-builder

Build branded, fully editable PowerPoint decks from markdown or spreadsheets, using a real PowerPoint template as the design system.

deck-builder is for people who have to ship real decks in a fixed template. You, or an agent, write the content; the engine owns layout, styling and validation. Every slide fills a template placeholder, nothing is improvised, and anything that doesn't fit fails a check with a code that says how to fix it. The same input always builds the same file.

- **Editable output.** Real text in template placeholders, native PowerPoint charts and tables, speaker notes. No slides made of images.
- **Markdown or Excel, interchangeably.** `deck.md` and `deck.xlsx` hold the same deck and convert into each other without loss, so a deck can start in markdown, go to a team as a workbook, and build from either.
- **Brands as data.** A brand kit is a template plus two YAML files. Generate one from your colors, fonts and logo, wrap an existing client template, or use the neutral example.
- **Visual QA that's cheap to read.** Renders with PowerPoint on a Mac or with LibreOffice, measures text overflow from the rendered PDF, and flags only the slides that need a look.
- **One CLI for people and agents.** Terse output by default, `--json` for agents, stable issue codes. The Claude Code skills and subagent in this repo call the same CLI.
- **Local.** The engine makes no network calls and sends nothing anywhere.

## Quick start

Needs [uv](https://docs.astral.sh/uv/). Rendering also needs poppler and either Microsoft PowerPoint (Mac) or LibreOffice.

```bash
git clone <this repo> deck-builder && cd deck-builder
uv sync
uv run deck-builder doctor          # what this machine can do, with install commands for anything missing
uv run deck-builder init            # workspace/, config, the neutral brand, two example decks
uv run deck-builder check workspace/decks/quarterly-review/deck.md --render
```

That last command validates, builds `workspace/out/quarterly-review.pptx`, renders it, and writes slide PNGs and a contact sheet beside it.

**With Claude Code:** open the clone and start a session. Onboarding runs the steps above with you, then helps you set up your own brand.

## A deck

````markdown
---
brand: neutral
title: Pemberton Paper Co. Q3 review
---

## Copy paper drove the growth
layout: content

- Copy paper volume rose 18% over Q2
- **Card stock** held flat

Notes:
Source: Q3 shipment ledger.

## 12%
layout: big-number
caption: Total volume growth, Q2 to Q3

## Cases shipped by month
layout: chart

```chart
type: column
categories: [Jul, Aug, Sep]
series:
  - name: Copy paper
    values: [9800, 10400, 11250]
```
````

One heading is one slide. `deck-builder docs deck-md` has the full format, and `deck-builder brand show neutral` lists the layouts, their fields and their character budgets.

## Commands

| Command | Does |
|---|---|
| `init` | Create the workspace, config, neutral brand and example decks |
| `doctor` | Check Python packages, poppler, LibreOffice, PowerPoint and its automation permission |
| `check <deck> [--render]` | Validate a deck; with `--render`, also build, render and measure |
| `build <deck> [--data rows.csv]` | Build the `.pptx` and its manifest; with `--data`, one deck per row |
| `convert <in> <out>` | Convert between `.md`, `.xlsx` and `.csv`, refusing anything lossy |
| `render <pptx>` | PDF, slide PNGs, contact sheets, measured overflow, flagged slides |
| `brand list`, `brand show <slug>`, `brand check <slug>` | Find brands, see a brand's layouts and budgets, verify a kit |
| `brand init <slug> --from brand.yaml` | Generate a template and `tokens.yaml` from colors, fonts and logo |
| `brand adopt <slug> --template FILE` | Wrap an existing `.potx` or `.pptx` as a brand |
| `inspect <template>` | A template's layouts, placeholders and theme |
| `assets <brand or deck>` | Logos, icons, colors and images, with the slides that use them |
| `docs [topic]`, `explain <CODE>` | Reference topics and issue-code fixes, matching the installed version |
| `skills install` | Link this clone's skills and agent into `~/.claude` for use in other repos |

Every command takes `--json`. Exit codes: 0 success, 1 issues to fix, 2 usage or environment problems. [docs/issue-codes.md](docs/issue-codes.md) lists every code.

## Brands

```
workspace/brands/<slug>/
  brand.yaml       # palette, fonts, logos, icons, voice, lint rules
  tokens.yaml      # layouts -> template placeholders, with content budgets
  template.potx    # the design: masters, layouts, theme
  assets/          # logos and icons
```

Decks name a brand with `brand: <slug>`. Brands are found under the `brand_paths` in `deck-builder.toml`, so a client's kit can live in its own private repo. Client material never belongs in this repo: everything under `workspace/` is gitignored.

## Claude Code

| Piece | Job |
|---|---|
| `deck-onboard` skill | Setup, missing tools, choosing a brand path, a first deck |
| `deck-brand` skill | Brand kits: colors, fonts, logos, icons, layouts, templates |
| `deck-builder` skill | Writing, checking, converting, building and reviewing decks |
| `deck-builder-agent` | The build loop for a larger deck, in its own context; the main agent reviews its work |

The engine does all deterministic work, so the model spends tokens on content and review. The engine is local; when you use the Claude Code layer, what the agent reads is sent to Anthropic like any Claude Code session.

## Status

v0.1.0. The PowerPoint render backend hasn't been verified on a real Mac yet; its results include the warning `RENDER_UNVERIFIED` until `scripts/probe_powerpoint.sh` passes. See [SPEC.md](SPEC.md) for the full design and [CHANGELOG.md](CHANGELOG.md) for changes.

## Development

```bash
uv run pytest                 # unit, round-trip and static tests, plus the render tier when LibreOffice is installed
uv run pytest -m render       # render tier only
uv run ruff check && uv run mypy
```

## License

MIT. See [LICENSE](LICENSE).
