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

`doctor` lists each requirement as ok, missing or optional, with the install command. Offer the
command for anything missing and wait for the user to run it or approve it. What each tool is
for:

| Tool | Needed for |
|---|---|
| poppler | Rendering and overflow measurement |
| Microsoft PowerPoint | Exact renders on a Mac; preferred when present |
| LibreOffice | Renders when PowerPoint isn't installed |
| rsvg-convert | Optional: SVG icons in brand kits |

Building and checking decks needs none of these. Without poppler and a renderer, the user can
build but not see renders.

If `doctor` reports PowerPoint's automation permission as denied, walk them to System Settings
> Privacy & Security > Automation, and have them allow the app running Claude Code to control
Microsoft PowerPoint.

## 2. Create the workspace

```
uv run deck-builder init
```

This creates `workspace/` (brands, decks, output; all gitignored), `deck-builder.toml`, and the
neutral example brand. Running it again changes nothing.

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

Copy an example into the workspace, point it at their brand, build and render it:

```
cp -R examples/decks/quarterly-review workspace/decks/
uv run deck-builder build workspace/decks/quarterly-review/deck.md
uv run deck-builder render workspace/out/quarterly-review.pptx
```

Open the first contact sheet with them and say what they're looking at. Then show the workflow
for their own decks: `uv run deck-builder docs workflow`.

## 5. Optional: use from other repos

`uv tool install .` puts `deck-builder` on their PATH. `deck-builder skills install` shows the
links it would create for the skills and agent; with their OK, rerun it with `--yes`.
