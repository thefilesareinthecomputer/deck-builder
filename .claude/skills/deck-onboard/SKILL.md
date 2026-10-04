---
name: deck-onboard
description: >-
  Walks a new user through setting up deck-builder after cloning - checking dependencies and
  render backends with doctor, creating the workspace with init, choosing a brand path (skip,
  bring your own template, starter, or full brand kit), and building and rendering a first
  deck. MUST be used the first time deck-builder runs in a clone, when no deck-builder.toml
  resolves, when the user asks to set up, install, onboard or get started, and when doctor
  reports a missing tool. Also installs the skills for use from other repos on request.
license: MIT
---

# deck-onboard

Assume the user may not be technical. Explain each step in a sentence before running it, run
one step at a time, and wait for them whenever a step needs them to install something or
make a choice.

## 1. Check the machine

```
uv sync                         # from the repo root; installs the Python dependencies
uv run deck-builder doctor
```

`doctor` lists each requirement as `ok`, `missing`, `optional`, `unverified` or `stale`, with the install
command after `fix:`, and ends with whether building is ready and which renderer will be used.
If `uv` is missing, offer two paths and let them pick: install uv (https://docs.astral.sh/uv/, one
command), or skip it with `pipx install .` (or `pip install .` in a virtual environment; Python
3.11 or later). Without uv, run `deck-builder doctor` instead, and use `deck-builder` wherever a
step below says `uv run deck-builder`; the step 2 install is then already done. Offer the install
command for anything missing and wait for the user to run it or approve it. What each tool is for:

| Tool | Needed for |
|---|---|
| poppler | Rendering and overflow measurement |
| LibreOffice | Renders; the verified backend, and what `auto` uses when it's installed |
| Microsoft PowerPoint | Renders on a Mac when LibreOffice isn't installed; not yet verified |

Building and checking decks needs none of these. Without poppler and a renderer, the user can
build but not see renders.

With PowerPoint installed, `doctor` shows it as `unverified`: its render backend hasn't been
proven on a real Mac yet. With their OK, `uv run deck-builder doctor --powerpoint` tests it; this
opens PowerPoint, and the first time macOS asks to let the app running Claude Code control it.
If they denied it, walk them to System Settings > Privacy & Security > Automation and have them
allow it. `scripts/probe_powerpoint.sh <deck.pptx>` runs the full check of that backend.

## 2. Create the workspace

```
uv run deck-builder init
```

This creates `workspace/` (brands, decks, output; all gitignored), `deck-builder.toml`, the neutral
example brand and two example decks in `workspace/decks/`. Running it again changes nothing.

To keep their decks in a folder outside the clone, run `uv run deck-builder init --dir <path>`
from the clone (it creates the folder if needed). Then work from that folder with
`uv run --project <clone> deck-builder ...`; the CLI finds that folder's `deck-builder.toml`.

Then install the CLI on their PATH, with their OK: `uv tool install <clone>` (the most common
setup; `--editable` only for someone changing the engine). Without uv, use `pipx install <clone>`,
or `pip install <clone>` in a virtual environment; any Python 3.11 or later works. The subagents have no shell and run
the engine through `deck-builder mcp`, so they need it. Confirm with `deck-builder doctor`: the
`agent tools (mcp)` row should be `ok`. To use the skills in their other Claude Code projects too,
run `deck-builder skills install` from the clone, show them the plan it prints, and rerun with
`--yes` after they agree.

## 3. Choose a brand path

Ask which fits, in plain words:

1. **Skip for now:** use the neutral example brand and see a deck first.
2. **Bring your own template:** they have a `.potx` or `.pptx` to build in.
3. **Starter brand:** their colors, fonts and logo on a standard layout set; improve later.
4. **Full brand kit:** palette, fonts, logos, icons, layouts, voice and rules, then polish in
   PowerPoint.

Options 2 to 4 hand off to the `deck-brand` skill, which comes back here when the kit passes
`deck-builder brand check`.

## 4. First deck

Build and render the example deck. If they set up their own brand, change `brand: neutral` in
the deck's front matter to their slug first.

```
uv run deck-builder check workspace/decks/quarterly-review/deck.md --render
```

That builds `workspace/out/quarterly-review.pptx`, renders it, and writes the slide PNGs and a
contact sheet to `workspace/out/quarterly-review.render/`. Open `contact-01.png` with them and say
what they're looking at, then point them at the `.pptx` to open in PowerPoint or Keynote.
`workspace/decks/bulk-outreach/` is the one-deck-per-row example; its `deck.md` names the command.
Then show the workflow for their own decks: `uv run deck-builder docs workflow`.

## 5. Optional: use from other repos

With the CLI installed (step 2), from the clone, `uv run deck-builder skills install` shows the
links it would create in `~/.claude` for the skills and the agents; with their OK, rerun it with
`--yes`. It refuses until `deck-builder` is on their PATH. The links point back at this clone, so a
`git pull` here updates them everywhere. Other repos can keep their own `deck-builder.toml` with
`brand_paths` pointing at their brand kits.
