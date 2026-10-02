# deck-builder

This repo is a PowerPoint deck builder: a deterministic engine (`src/deck_builder/`, the
`deck-builder` CLI) plus a Claude Code layer that drives the same CLI.

## First run

If `uv run deck-builder brand list` reports no config, the user hasn't onboarded yet. Run the
`deck-onboard` skill before anything else.

## Division of labor

- The engine parses, converts, validates, builds, renders and measures. It never calls the network.
- You write content (`deck.md` or a workbook) and `brand.yaml`, and you judge results.
- You never write python-pptx code or PowerPoint XML for a deck, and never edit a built `.pptx`.
- Brand kits (`brand.yaml`, `tokens.yaml`, templates) change only when the user asks.

| Task | Skill or agent |
|---|---|
| Setup, missing tools, first deck | `deck-onboard` skill |
| Brand kits: colors, fonts, logos, icons, layouts, templates | `deck-brand` skill |
| Writing, converting, building, rendering decks | `deck-builder` skill |
| The build loop for a deck of more than a handful of slides | `deck-builder-agent` subagent, then the review gate in the `deck-builder` skill |

## Working on the engine itself

- `uv run pytest`, `uv run ruff check`, `uv run mypy` must pass before a commit.
- `SPEC.md` is the contract; `tasks/plan.md` is the build order.
- When a skill needs something the CLI can't do, add it to the CLI. Skills hold no engine logic.
- Example content uses invented companies only. No client material in tracked files.
