<h1 align="center">deck-builder</h1>

<p align="center">
  Branded, fully editable PowerPoint decks from markdown or a spreadsheet,<br>
  using a real PowerPoint template as the design system.
</p>

<p align="center">
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-2EA44F">
</p>

<p align="center">
  <a href="#quick-start"><b>Quick start</b></a> &nbsp;|&nbsp;
  <a href="#how-it-works"><b>How it works</b></a> &nbsp;|&nbsp;
  <a href="#write-a-deck"><b>Write a deck</b></a> &nbsp;|&nbsp;
  <a href="#brands"><b>Brands</b></a> &nbsp;|&nbsp;
  <a href="#commands"><b>Commands</b></a> &nbsp;|&nbsp;
  <a href="#claude-code"><b>Claude Code</b></a>
</p>

<br>

<p align="center">
  <img src="docs/images/showcase.png" width="100%" alt="The same deck built in three brands: a dark green paper supplier set in Georgia, a navy office-systems company set in Avenir Next, and a charcoal soap maker set in Helvetica Neue. Each column shows the title slide, a native column chart and an image slide.">
</p>
<p align="center"><sub>One <code>deck.md</code>, built with three brand kits. Every chart is a native PowerPoint chart and every word is editable.</sub></p>

<br>

You or an agent write the content, and the engine handles layout, styling and validation. Every slide fills a placeholder in the template, and content that doesn't fit fails a check with a code that says how to fix it.

<table>
  <tr>
    <td width="33%" valign="top"><b>Editable output</b><br>Real text in template placeholders, native charts and tables, speaker notes and alt text.</td>
    <td width="33%" valign="top"><b>Markdown or Excel</b><br><code>deck.md</code> and <code>deck.xlsx</code> convert into each other without loss, and either one builds the deck.</td>
    <td width="33%" valign="top"><b>Brands as data</b><br>A brand kit is a template plus two YAML files. Generate one from your colors, fonts and logo, or wrap an existing template.</td>
  </tr>
  <tr>
    <td valign="top"><b>Existing decks, made consistent</b><br><code>import</code> turns a .pptx back into <code>deck.md</code>, drops one-off formatting and reports what needs a decision.</td>
    <td valign="top"><b>Visual QA</b><br>Renders with PowerPoint or LibreOffice, measures where every word landed, and flags only the slides that need a look.</td>
    <td valign="top"><b>Deterministic and local</b><br>The same input builds the same file, and the engine makes no network calls.</td>
  </tr>
</table>

## Quick start

You need [uv](https://docs.astral.sh/uv/). Rendering also needs LibreOffice (or PowerPoint on a Mac) and poppler, and `uv run deck-builder doctor` checks for them.

```bash
git clone <this repo> deck-builder && cd deck-builder
uv run deck-builder init
uv run deck-builder check workspace/decks/quarterly-review --render
```

`init` creates a workspace with a neutral brand and two example decks. `check --render` builds the first one into `workspace/out/quarterly-review.pptx` and renders it, with a contact sheet next to it.

To run `deck-builder` from any folder, install it once with `uv tool install --editable .`

> [!TIP]
> **Using Claude Code?** Open the clone and start a session. Onboarding runs these steps with you, then sets up your own brand.

## How it works

1. **Write** the content in `deck.md` or `deck.xlsx`.
2. **Check** it. Unknown layouts, missing images and text over a field's character budget fail with an issue code.
3. **Build** the `.pptx` from the brand's template.
4. **Render** it and review the contact sheet. Words that overflow their box, empty placeholders and substituted fonts get flagged.

Fix what's flagged and run it again; `deck-builder explain <CODE>` prints the cause and fix for any issue code. `check --render` runs steps 2 to 4 in one command.

<p align="center">
  <img src="docs/images/contact-sheet.png" width="100%" alt="A contact sheet of nine rendered slides labeled slide 1 to slide 9, the image an agent reviews after a render.">
</p>
<p align="center"><sub>A render's contact sheet. Flagged slides get a red border, so a reviewer reads one image instead of nine.</sub></p>

## Write a deck

One `##` heading is one slide. `key: value` lines fill the layout's fields, and the rest fills its body. These three slides are the first column of the image at the top:

````markdown
---
brand: briarfield-paper
title: Briarfield Paper Co. Q3 review
---

## Briarfield Paper Co. Q3 review
layout: title
subtitle: Volume, delivery and the plan for Q4

## Cases shipped by month
layout: chart

```chart
type: column
number_format: '#,##0'
labels: true
categories: [Jul, Aug, Sep]
series:
  - name: Core line
    values: [9800, 10400, 11250]
  - name: Specialty
    values: [3100, 3050, 3120]
```

Notes:
Source: the Q3 shipment ledger.

## The new north warehouse
layout: image
caption: "Opened in August: same-day delivery for the northern accounts."

![The new north warehouse](assets/hero.png)
````

Field values are YAML, so quote a value that contains `: `. `deck-builder brand show <slug>` lists a brand's layouts, fields and character budgets. The [full showcase deck](tests/fixtures/demo-brands/showcase/deck.md) builds into all three brands in one command with `build --data`.

## Brands

```
brands/<slug>/
  brand.yaml       # palette, fonts, logos, icons, voice, lint rules
  tokens.yaml      # layouts -> template placeholders, with content budgets
  template.potx    # the design: masters, layouts, theme
  assets/          # logos and icons
```

| Starting point | Command |
|---|---|
| Your colors, fonts and logo | `deck-builder brand init <slug> --from brand.yaml` generates the template and `tokens.yaml` |
| An existing template | `deck-builder brand adopt <slug> --template client.potx` wraps it; a test render then tunes the budgets |
| Nothing yet | The `neutral` brand that `init` creates |

A deck names its brand with `brand: <slug>`, and `--brand` overrides it for one build. Brands are found under `brand_paths` in `deck-builder.toml`, so a client's kit can live in its own private repo. Nothing under `workspace/` is committed.

## Commands

| Command | Does |
|---|---|
| `init` | Create the workspace, config, neutral brand and example decks |
| `doctor` | Check Python packages, poppler, LibreOffice, PowerPoint and its automation permission |
| `check <deck> [--render]` | Validate a deck; with `--render`, also build, render and measure |
| `build <deck> [--data rows.csv]` | Build the `.pptx` and its manifest; with `--data`, one deck per row |
| `convert <in> <out>` | Convert between `.md`, `.xlsx` and `.csv`, refusing anything lossy |
| `import <pptx> <out>` | Turn an existing deck back into `deck.md`, its images and a report of what needs a decision |
| `render <pptx>` | PDF, slide PNGs, contact sheets, measured overflow, flagged slides |
| `brand list`, `brand show <slug>`, `brand check <slug>` | Find brands, see a brand's layouts and budgets, verify a kit |
| `brand init`, `brand adopt` | Generate a kit, or wrap an existing template |
| `inspect <template>` | A template's layouts, placeholders and theme |
| `assets <brand or deck>` | Logos, icons, colors and images, with the slides that use them |
| `docs [topic]`, `explain <CODE>` | Reference topics and issue-code fixes for the installed version |
| `skills install` | Link this clone's skills and agents into `~/.claude` |

A `<deck>` is a `.md`, `.xlsx` or `.csv` file, or a folder holding one. Every command takes `--json`. Exit codes are 0 for success, 1 for issues to fix and 2 for usage or environment problems. `deck-builder docs` lists the reference topics, and [docs/issue-codes.md](docs/issue-codes.md) lists every issue code.

## Claude Code

| Piece | Job |
|---|---|
| `deck-onboard` skill | Setup, missing tools, choosing a brand path, a first deck |
| `deck-brand` skill | Brand kits: colors, fonts, logos, icons, layouts, templates |
| `deck-builder` skill | Writing, checking, converting, building and reviewing decks |
| `deck-decomposer-agent` | Turns a folder of notes into an outline with sources and a draft `deck.md` to co-author |
| `deck-brand-agent` | Builds or adopts a brand kit and tunes its budgets with a test render |
| `deck-builder-agent` | Runs the check, build and render loop on a larger deck in its own context |

The agents have no shell. They reach the engine only through its MCP server (`deck-builder mcp`), confined to the workspace, so the CLI has to be on PATH (`uv tool install --editable <clone>`). `deck-builder skills install` adds the skills and agents to `~/.claude` for use in other repos.

> [!NOTE]
> The engine is local, but what an agent reads goes to Anthropic, as in any Claude Code session. Agents can still write files the session allows, so keep client work outside the clone.

## Rules the engine keeps

- **Content in, design out.** Decks hold text, data and image references. Layout, fonts and colors come only from the brand kit, and budgets aren't loosened to make content fit.
- **Confined.** A deck reads images only inside its folder, a build writes only the `.pptx` files it made, and bulk data can't add slides or images. Imported decks are untrusted input.
- **Restraint.** Visual additions such as slide numbers, footers and status dots are the smallest mark that does the job.

## Status

v0.1.0. See [CHANGELOG.md](CHANGELOG.md). Known limits:

- The PowerPoint render backend hasn't been verified on a Mac with PowerPoint, so its renders warn `RENDER_UNVERIFIED`. LibreOffice renders are a close proxy.
- Icons are PNG alpha masks; SVG isn't supported.

## Development

```bash
uv run pytest                          # unit, round-trip and static tests, plus the render tier when LibreOffice is installed
uv run pytest -m render                # render tier only
uv run ruff check && uv run mypy
uv run python scripts/readme_images.py # regenerate the images in this README
```

The three fictional brands in `tests/fixtures/demo-brands/` are the test and showcase brands; their names and artwork were made for this repo. Releases follow [docs/release-checklist.md](docs/release-checklist.md).

## License

MIT. See [LICENSE](LICENSE).
