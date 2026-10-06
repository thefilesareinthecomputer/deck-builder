<h1 align="center">deck-builder</h1>

<p align="center">
  Write your slides in markdown or Excel and get back a real, editable PowerPoint deck on your own brand template.<br>
  The same input always gives the same file, every slide gets checked, and a guided setup gets you to your first deck.
</p>

<p align="center">
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-2EA44F">
</p>

<p align="center">
  <a href="#install"><b>Install</b></a> &nbsp;|&nbsp;
  <a href="#quick-start"><b>Quick start</b></a> &nbsp;|&nbsp;
  <a href="#how-it-works"><b>How it works</b></a> &nbsp;|&nbsp;
  <a href="#write-a-deck"><b>Write a deck</b></a> &nbsp;|&nbsp;
  <a href="#example-decks"><b>Examples</b></a> &nbsp;|&nbsp;
  <a href="#fix-up-an-existing-deck"><b>Fix up a deck</b></a> &nbsp;|&nbsp;
  <a href="#brands"><b>Brands</b></a> &nbsp;|&nbsp;
  <a href="#commands"><b>Commands</b></a> &nbsp;|&nbsp;
  <a href="#claude-code"><b>Claude Code</b></a> &nbsp;|&nbsp;
  <a href="#updating"><b>Updating</b></a>
</p>

<br>

<p align="center">
  <img src="docs/images/showcase.png" width="100%" alt="The same deck built in three brands: a dark green paper supplier set in Georgia, a navy office-systems company set in Avenir Next, and a charcoal soap maker set in Helvetica Neue. Each column shows the title slide, three cards with colored labels and a bold target line, and a native column chart under a section label and subtitle, with its takeaway.">
</p>
<p align="center"><sub>One <code>deck.md</code>, built three times with three different brands. Each brand sets its own type, card colors and takeaway style. The charts are real PowerPoint charts, and every word is still editable.</sub></p>

<br>

You (or an agent) write the content. deck-builder puts every piece of it into a placeholder in your PowerPoint template, so the fonts, colors and layout always come from your brand. If something doesn't fit, `check` tells you what's wrong and how to fix it.

<table>
  <tr>
    <td width="33%" valign="top"><b>Built on your template</b><br>Make a brand kit from your colors, fonts and logo, or use the PowerPoint template your team already has.</td>
    <td width="33%" valign="top"><b>Markdown or Excel</b><br>Write in <code>deck.md</code> or <code>deck.xlsx</code>. They convert back and forth without losing anything, so writers and reviewers can each use the one they like.</td>
    <td width="33%" valign="top"><b>Guided setup</b><br>In <a href="https://code.claude.com/docs/en/overview">Claude Code</a>, Anthropic's coding agent, onboarding checks your setup, sets up your brand and builds a first deck with you.</td>
  </tr>
  <tr>
    <td valign="top"><b>Same input, same file</b><br>A build always gives you the same file for the same input, and the engine never goes online.</td>
    <td valign="top"><b>Native and editable</b><br>You get real text in the template's placeholders, real charts and tables, speaker notes and alt text. Nothing gets flattened into a picture.</td>
    <td valign="top"><b>Checked by eye and by measure</b><br>Each render measures where every word ended up and flags only the slides you need to look at.</td>
  </tr>
</table>

## Install

You need Python 3.11 or later. The commands below use [uv](https://docs.astral.sh/uv/), which is the quickest way in, but pipx and pip work too. To render slides you also need poppler and LibreOffice. PowerPoint on a Mac can render as well, but we haven't verified it yet. `deck-builder doctor` tells you what's installed.

```bash
git clone https://github.com/thefilesareinthecomputer/deck-builder.git && cd deck-builder
uv tool install .                     # deck-builder on your PATH, for you and for Claude Code's agents
deck-builder skills install --yes     # optional: the skills and agents in every Claude Code project
```

| Use it | Set up with | You get |
|---|---|---|
| **As a tool for agents and the CLI** (most common) | `uv tool install .` | `deck-builder` in any folder, plus the MCP server (`deck-builder mcp`) the agents use |
| **As a skill in your other Claude Code projects** | `deck-builder skills install --yes`, after the tool | The three skills and five agents, linked into `~/.claude` |
| **From the clone**, to try it or work on it | `uv run deck-builder ...` | No install; a Claude Code session opened in the clone already has the skills |

**Without uv:** `pipx install .`, or `pip install .` inside a virtual environment, puts the same `deck-builder` command on your PATH. Then run `deck-builder skills install --yes` as above.

If you're working on the engine itself, install with `--editable` so the tool runs straight from the clone. To get a newer version later, see [Updating](#updating).

## Quick start

```bash
deck-builder init --dir ~/decks       # a workspace: config, the neutral brand, two example decks
cd ~/decks
deck-builder check workspace/decks/quarterly-review --render
```

`check --render` checks the example deck, builds it and renders it. The deck lands in `workspace/out/quarterly-review.pptx`, and its slide images and contact sheet go in `workspace/out/quarterly-review.render/`.

> [!TIP]
> **Using Claude Code?** Just ask: "set up deck-builder", "make a deck from these notes", "fix the fonts in this deck". Onboarding walks through these steps with you and then sets up your brand.

## How it works

A deck is a text file. Each `##` heading starts a slide, and its `layout:` line picks one of the brand's layouts. Each layout has fields, like title, subtitle, body and caption, and each field maps to a placeholder in the template. Every field also has a character budget, which is the most text that fits in its box.

1. **Write** the content in `deck.md` or `deck.xlsx`.
2. **Check** it with `deck-builder check`. If the brand doesn't have a layout, an image is missing or text runs over its budget, you get an issue code, and `deck-builder explain <CODE>` tells you the cause and the fix.
3. **Build** the `.pptx`. Every piece of text goes into a template placeholder, so the fonts, colors and positions all come from the template.
4. **Render** the `.pptx` to images and look over the contact sheet, which puts up to 20 slides on one image. The render measures where each word landed and flags any slide with text running over, an empty placeholder or a swapped-in font.

`check --render` does steps 2 to 4 in one go, and that's what the quick start ran. Fix any flagged slides in the deck file and run it again.

<p align="center">
  <img src="docs/images/contact-sheet.png" width="100%" alt="A contact sheet of eleven rendered slides labeled slide 1 to slide 11: title, agenda, three cards, a chart, a big number, three risk bands, a table, an image beside bullets, a row of partner logos, three icons and a closing slide. It is the image an agent reviews after a render.">
</p>
<p align="center"><sub>A contact sheet from a clean render. A flagged slide gets a red border and a label, so you can find it without opening every slide.</sub></p>

## Write a deck

A deck and a brand are separate things. The deck only holds content: text, data and image references. It names its brand with one line, `brand: <slug>`. The brand kit holds the whole design: the template, fonts, colors, logos and budgets. Change that one line, or pass `--brand <slug>`, and the same content builds in a different design. The image at the top is one deck built that way three times.

Each `key: value` line under a heading fills one of the layout's fields, and the rest of the slide goes into the body. `### name` starts the content for a named field, like each card's bullets. The three slides below are the first column of that image. They use the `dumbder-nifftlin` demo brand; to try them in your quick-start workspace, change the brand to `neutral`.

````markdown
---
brand: dumbder-nifftlin
title: Dumbder Nifftlin Paper Co. Q3 review
kicker: Q3 review
---

## Dumbder Nifftlin Paper Co. Q3 review
layout: title
subtitle: Volume, delivery and the plan for Q4

## Three bets for Q4
layout: cards-3
kicker: The plan
label1: Monthly invoicing
footer1: "Target: 40 accounts"
label2: Same-day delivery
footer2: "Target: 95% same-day"
label3: Recycled reporting
footer3: "Target: 12 accounts"
takeaway: The three bets add about 9% to Q4 revenue

### body1
- One invoice a month
- Pilot with ten accounts
- All accounts by December

### body2
- North region in October
- Two new evening routes
- Every order tracked

### body3
- **Recycled** share on invoices
- A quarterly summary

## Cases shipped by month
layout: chart
kicker: Volume
subtitle: The core line set a record in September
takeaway: The core line grew every month while specialty held flat

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
````

Field values are YAML, so put quotes around any value with `: ` in it. `deck-builder brand show <slug>` lists a brand's layouts, fields and budgets. The [full showcase deck](tests/fixtures/demo-brands/showcase/deck.md) builds into all three brands with one `build --data` command.

You can also write a deck as a spreadsheet. In `deck.xlsx` each slide is a row, and charts and tables get their own sheets. A plain `deck.csv` works for decks that are only text, and `build --data rows.csv` builds one deck per row from a template deck.

Code goes in a fenced block with its language. It builds as real, editable text, highlighted in the brand's colors on a panel sized to fit, and it never wraps. If a line is too long for the panel, `check` tells you. `{6-8}` highlights lines, `lines` adds line numbers, and `title=` shows the file name. This is the first slide in the grid below:

````markdown
## The web form now saves each line
layout: code
subtitle: A timeout used to drop the basket; now it loses a line at most

```python {6-8} lines title="orders/basket.py"
def add_line(basket, item, quantity):
    line = OrderLine(basket.id, item.sku, quantity)
    if not item.in_stock(quantity):
        raise OutOfStock(item.sku)
    basket.lines.append(line)
    # save now, so a later timeout can't drop it
    db.session.add(line)
    db.session.commit()
    return line
```
````

A few more options help with emphasis and pacing. `layout: statement` puts one sentence in large type. `layout: image-full` runs a photo edge to edge with the title on a band across the bottom. `build: <field>` fades a list, a chart or a set of cards in one click at a time while you present. In a long deck, `current: n` on the agenda shows which part you're in.

Screenshots are shown whole and photos fill their box. `layout: image-2` puts two screens side by side. A `SCREENSHOT:` line in a slide's notes names a capture the slide should show, and `check` warns when the slide's layout can't show it, with the layouts that can and what moving costs. `deck-builder assets --images <deck>` lists every image and whether it's shown, cropped, only in the notes, missing or unused.

## Example decks

<p align="center">
  <img src="docs/images/decks.png" width="100%" alt="Nine slides from the three demo brands' decks, one column per brand. Dark green and tan paper supplier: a Python function on a dark code panel with three highlighted lines, a column chart of on-time delivery against the regional average, and three labeled risk bands. Navy and orange office-systems company: a navy title slide, five process chevrons in a ramp of navy, and a line chart of planned against actual installs. Charcoal and terracotta soap maker: a stacked column chart of revenue by channel, a photo of soap bars beside four bullets, and three cards with charcoal labels.">
</p>
<p align="center"><sub>Nine slides from the demo brands' pitch and review decks, one column per brand. Each brand sets its own type, colors, chart palette, code panel and takeaway style.</sub></p>

## Design

Every generated kit follows one design standard, based on presentation research; `deck-builder docs design` has the full rules. Titles are bold sentences in the same spot on every slide. Short content sits at the optical center instead of hugging the top. Comparisons go on tinted panels.

Tables stay quiet, with a dark header, thin rules, numbers aligned right and no word ever split across lines. Charts stay quiet too. Bars start at zero, gridlines are hairlines, axis labels are muted, and a bar chart with labels drops its scale. We show shares of a whole as sorted bars and don't use pies or doughnuts. Code sits on a quiet panel in a monospace font, with bold keywords and italic comments, and every color in it reads at 4.5:1. An optional `takeaway:` band states each slide's conclusion, and one short accent rule is the only decoration. Slides never animate from one to the next. The only motion is a half-second fade inside a slide, and only where you ask for it.

Set `generate.mode` in `brand.yaml` to match how the deck will be used. `projected`, the default, is for presenting to a room, so nothing goes under 18 pt. `read` is for decks people read on their own screen, with a 14 pt body at a comfortable line length. `generate.type` changes any single size.

`generate.layout_set: designed` adds layouts built from shapes instead of loose text: two to five cards with colored labels, three to six process chevrons, two to four labeled bands and a row of logos. It also adds a section label and a subtitle line to every content slide. Options give icons a tile, give each process step an icon, and switch the takeaway to an italic line. Images with transparent backgrounds, like logos, get fitted inside their box instead of cropped, and every brand can use the engine's starter icons.

Accessibility follows WCAG 2.2 AA, the standard that accessibility laws point to. Generated layouts keep projected text at 18 pt or more and white labels at 4.5:1 contrast. `brand check` warns about color pairs under the WCAG ratios, chart colors that look alike to people with color blindness, and type that's too small. `check` warns about images without alt text, two slides with the same title, charts that rely on color alone, and filler words like "leverage" or "dramatically". These are warnings rather than errors, because colors stay the brand owner's call. `deck-builder docs design` has the details.

## Fix up an existing deck

To clean up a deck (its fonts, sizes, colors and slide numbers) or move it onto your brand, import it and rebuild it:

```bash
deck-builder import old.pptx workspace/decks/refresh --brand <slug>
deck-builder check workspace/decks/refresh --render
```

`import` turns the .pptx back into `deck.md` plus its images. The rebuild takes every style from the brand and numbers every content slide. Your original file is never touched. Anything that doesn't fit a layout field, like SmartArt or a stray text box, goes into `import-report.md` and into that slide's speaker notes, so nothing gets lost. In Claude Code, just ask: "fix the fonts and slide numbers in this deck" or "put this deck on our brand".

## Brands

```
brands/<slug>/
  brand.yaml       # the recipe: palette, fonts, logos, icons, voice, lint rules, mode and type scale
  assets/          # the ingredients: logos and icons
  template.potx    # generated: masters, layouts, theme
  tokens.yaml      # generated: layouts -> placeholders, budgets, table and chart styling, what made the kit
  references/      # optional: past decks to match, read-only
```

A generated kit has everything it needs. `brand init <slug> --force` rebuilds it from its own recipe and assets, and `brand check` warns with `KIT_STALE` if the recipe has changed since then.

| Starting point | Command |
|---|---|
| Your colors, fonts and logo | `deck-builder brand init <slug> --from brand.yaml` generates the template and `tokens.yaml` |
| An existing template | `deck-builder brand adopt <slug> --template client.potx` wraps it, and a test render then tunes the budgets |
| Nothing yet | The `neutral` brand that `init` creates |

A deck picks its brand with `brand: <slug>`, and `--brand` overrides that for one build. Brands are found through `brand_paths` in `deck-builder.toml`, so a kit can live in any folder.

## Commands

| Command | Does |
|---|---|
| `init` | Create the workspace, config, neutral brand and example decks |
| `doctor` | Check Python packages, poppler, LibreOffice, PowerPoint and its automation permission, and that the agents' tools start from this folder |
| `check <deck> [--render]` | Check a deck; with `--render`, also build, render and measure it |
| `build <deck> [--data rows.csv]` | Build the `.pptx` and its manifest; with `--data`, one deck per row |
| `convert <in> <out>` | Convert between `.md`, `.xlsx` and `.csv`, refusing anything that would lose content |
| `import <pptx> <out>` | Turn an existing deck back into `deck.md`, its images and a report of what needs a decision |
| `render <pptx>` | PDF, slide PNGs, contact sheets, measured overflow and flagged slides |
| `brand list`, `brand show <slug>`, `brand check <slug>` | Find brands, see a brand's layouts and budgets, and check a kit |
| `brand init`, `brand adopt` | Generate a kit, or wrap an existing template; `brand init <slug> --force` regenerates a kit from its own `brand.yaml` |
| `brand add-asset <slug> <png> --as logo/<id>` | Copy a logo or icon (`icon/<id>`) into a kit |
| `brand copy <slug> <new-slug>` | Copy a kit under a new slug, tuned budgets and template edits included, to rename or version a brand; the original stays as it is |
| `inspect <template>` | A template's layouts, placeholders and theme |
| `assets <brand or deck>` | Logos, icons, colors and images, with the slides that use them; `--images` says where each of a deck's images lands |
| `docs [topic]`, `explain <CODE>` | Reference topics and issue-code fixes for the installed version |
| `schema brand\|tokens\|manifest` | The JSON Schema for `brand.yaml`, `tokens.yaml` or a build manifest |
| `skills install` | Link this clone's skills and agents into `~/.claude` |
| `mcp` | Serve the engine as MCP tools over stdio for the agents, kept inside the workspace |

A `<deck>` can be a `.md`, `.xlsx` or `.csv` file, or a folder with one in it. Every command takes `--json`. The exit code is 0 for success, 1 when there are issues to fix and 2 for a usage or setup problem. `deck-builder docs` lists the reference topics, and [docs/issue-codes.md](docs/issue-codes.md) explains every issue code.

## Claude Code

deck-builder comes with skills and agents for Claude Code. Describe the deck you need, from a brief or a folder of notes, and then review what it renders.

| Piece | Job |
|---|---|
| `deck-onboard` skill | Setup, missing tools, choosing where brands live, and a first deck |
| `deck-brand` skill | Brand kits: colors, fonts, logos, icons, layouts and templates |
| `deck-builder` skill | Writing, checking, converting, building and reviewing decks |
| `deck-decomposer-agent` | Turns a folder of notes into an outline with sources and a draft `deck.md` for you to edit |
| `deck-storyteller-agent` | Optional. Turns an outline, data or a scenario into a storyboard: the story's arc, the slide titles and how each slide should look, for the builder to write the deck from |
| `deck-brand-agent` | Builds or adopts a brand kit and tunes its budgets with a test render |
| `deck-builder-agent` | Runs the check, build and render loop on a bigger deck in its own context |
| `deck-validator-agent` | Proofreads a built deck against the design and accessibility rules, slide by slide, and signs it off or sends it back with fixes; it never edits |

The agents can't run shell commands. The decomposer and the storyteller run no commands at all. The other agents reach the engine only through its MCP server (`deck-builder mcp`), which keeps them inside the workspace (and the `brand_paths` folders for brand work) and always refuses this clone's own `src/`, `.claude/` and `.git/`. The CLI has to be on your PATH (`uv tool install .` from the repo). `deck-builder skills install --yes` makes the skills and agents available in your other projects.

## Principles

- **Content in, design out.** Decks hold text, data and image references. Layout, type and color come only from the brand kit, and budgets never get loosened to make content fit.
- **Confined by default.** A deck only reads images from its own folder, a build only writes the `.pptx` files it makes, and bulk data can't add slides or images. Imported decks are treated as untrusted. The MCP server keeps its tools inside the workspace (and `brand_paths` for brand work) and refuses this clone's own `src/`, `.claude/` and `.git/`. An agent's own Write and Edit tools are limited by its instructions, not by code.
- **Restraint.** Visual extras like slide numbers, footers and status dots use the smallest mark that does the job.

## Updating

Cloning and installing as above always gets you the latest code, so you don't need to pick a version. When a new one comes out, do this on each machine where you use deck-builder:

1. Commit or stash anything you're changing in the clone, then run `git pull`.
2. Reinstall the tool with `uv tool install --reinstall .`, or `uv tool install --editable --reinstall .` for an editable install (`pipx install --force .` without uv). Until you do, the tool keeps running the old version, and so do the agents, since they use the same install. If a new version needs a package your install doesn't have, every command stops and tells you to run this.
3. If you use the skills and agents in other projects, run `deck-builder skills install --yes` again so any new agent gets linked, and restart any open Claude Code sessions.
4. Run `deck-builder doctor`. It tells you if the installed tool is behind the clone, if an agent isn't linked, and which brand kits an older version made.
5. Read the release's "Upgrading" notes in the [changelog](CHANGELOG.md), then run `deck-builder check` on the decks you're working on.

Brand kits from an older version keep working; they just don't get the new layouts or styling. `deck-builder brand init <slug> --force` upgrades a kit by rebuilding it from its `brand.yaml`. That replaces any budgets you tuned and any edits you made to the template in PowerPoint, so it first copies the whole kit, as it was, into the kit's `backups/` folder. To upgrade one:

1. Run `deck-builder brand init <slug> --force`. It prints where it kept the old kit.
2. Run `deck-builder check <deck> --render` on your decks and look at the renders.
3. Copy any tuned budgets you still want from the backup's `tokens.yaml` into the new one; `brand init` lists the budgets that changed. To go back, copy the backup's files over the kit's.

To compare before touching the original, run `deck-builder brand copy <slug> <slug>-next` and upgrade the copy instead.

Kits adopted from a client's own template never change. Decks you've already built don't change either. Rebuilding a deck with a new version can change how it looks, and a rebuild won't replace a `.pptx` you've edited by hand unless you pass `--force`.

To stay on one version instead, install its tag: `uv tool install git+https://github.com/thefilesareinthecomputer/deck-builder@v0.2.0`.

## Status

The current release is v0.2.0, and the [changelog](CHANGELOG.md) lists what's in it. Known limits:

- We haven't verified the PowerPoint render backend on a Mac with PowerPoint yet, so its renders come with a `RENDER_UNVERIFIED` warning. LibreOffice renders are a close match.
- The in-slide fade (`build:`) is written for PowerPoint, and playing it there is part of that same check. LibreOffice reads it as its own fade.
- Icons are PNG masks; SVG isn't supported.

## Development

Read [CONTRIBUTING.md](CONTRIBUTING.md) before you open a pull request, and [SECURITY.md](SECURITY.md) to report a vulnerability.

```bash
uv run pytest                          # everything: unit and CLI integration tests, the scenario suite, and the render tier when LibreOffice is installed
uv run pytest -m render                # the render tier only
uv run ruff check && uv run mypy
uv run python scripts/readme_images.py # regenerate the images in this README
```

| Script | Does |
|---|---|
| `scripts/readme_images.py` | Builds the showcase deck and the brand decks the example grid draws from, in the three demo brands, and redraws `docs/images/` |
| `scripts/demo_brand_logos.py` | Redraws the demo brands' logo wordmarks from their SVG sources (macOS fonts) |
| `scripts/make_example_assets.py` | Draws the neutral brand's logo and icons and the example deck's image |
| `scripts/make_starter_icons.py` | Draws the engine's starter icons, which any brand can use |
| `scripts/probe_powerpoint.sh <deck.pptx>` | Tests the PowerPoint render backend on a Mac with PowerPoint |

The three made-up brands in `tests/fixtures/demo-brands/` are the test and showcase brands, and their names and artwork were made for this repo. Everything under `workspace/` is ignored by git, so the decks and brands you make there stay out of the repo. Releases follow the [release checklist](docs/release-checklist.md).

## License

Released under the [MIT License](LICENSE).
