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
| Brand kits: the conversation with the user | `deck-brand` skill |
| Brand kits: generating, checking and test-rendering a kit from those decisions | `deck-brand-agent` subagent |
| A deck from a large body of documents, notes or a knowledge base or vault | `deck-decomposer-agent` subagent writes `outline.md` and a draft `deck.md`; the user co-authors and proofreads before anything is built |
| Writing, converting, building, rendering decks | `deck-builder` skill |
| The build loop for a deck of more than a handful of slides | `deck-builder-agent` subagent, then the review gate in the `deck-builder` skill |

Subagents can't talk with the user. The main agent holds the conversation, hands each agent the
decisions it needs, relays the questions they return, and reviews their work before the user sees it.

The subagents have no shell. `deck-builder-agent` and `deck-brand-agent` reach the engine only
through the deck-builder MCP server (`deck-builder mcp`, which needs the CLI on PATH), confined to
the workspace; put their input files inside it. The decomposer runs no commands at all.

## Working on the engine itself

- `uv run pytest`, `uv run ruff check`, `uv run mypy` must pass before a commit.
- `README.md` and the reference topics (`deck-builder docs`) describe how the engine behaves; the
  original design spec is archived at `tasks/completed/SPEC-2026-10-02.md`.
- Agent files load at session start: test an edited agent in a fresh process, e.g.
  `claude -p --agent deck-builder-agent --allowedTools mcp__deck-builder "<test prompt>"`.
- When a skill needs something the CLI can't do, add it to the CLI. Skills hold no engine logic.
- Example content uses invented companies only. No client material in tracked files.
