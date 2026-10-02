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
- Brand kits (`brand.yaml`, `tokens.yaml`, templates) change only when the user asks. Styling goes
  there, never into engine code.
- Any edit to a `deck.md` goes through the `deck-builder` skill.
- Delegation threshold: 6 or more slides, or any restructure, goes to the `deck-builder-agent`
  subagent; get the user's OK on the storyline at the same threshold.
- Two rounds of check-and-fix, review send-backs or budget tuning, then stop and report to the
  user, so no loop runs unseen.

| Task | Skill or agent |
|---|---|
| Setup, missing tools, first deck | `deck-onboard` skill |
| Brand kits: the conversation with the user | `deck-brand` skill |
| Brand kits: generating, checking and test-rendering a kit from those decisions | `deck-brand-agent` subagent |
| A deck from a large body of documents, notes or a knowledge base or vault | `deck-decomposer-agent` subagent writes `outline.md` and a draft `deck.md`; the user co-authors and proofreads before anything is built |
| Writing, converting, building, rendering decks | `deck-builder` skill |
| The build loop at or past the delegation threshold above | `deck-builder-agent` subagent, then the review gate in the `deck-builder` skill |
| Final proofread and sign-off of a built deck, before it's called finished | `deck-validator-agent` subagent, run by the main agent at the review gate; its send-backs count toward the two rounds above |

Subagents can't talk with the user. The main agent holds the conversation, hands each agent the
decisions it needs, relays the questions they return, and reviews their work before the user sees it.

The subagents have no shell; put their input files inside the workspace before handing off, since
`deck-builder-agent`, `deck-brand-agent` and `deck-validator-agent` reach the engine only through the
deck-builder MCP server (`deck-builder mcp`, which needs the CLI on PATH), and the decomposer runs no
commands at all.
`deck-builder docs agents` maps every CLI command and MCP tool to the one party that owns it, and
says what each subagent may read and write.

## Working on the engine itself

- `uv run pytest`, `uv run ruff check`, `uv run mypy` must pass before a commit.
- `README.md` and the reference topics (`deck-builder docs`) describe how the engine behaves.
  `tasks/` holds local working notes (the handoff, plans, the archived design spec) and isn't tracked.
- Agent files load at session start: test an edited agent in a fresh process, e.g.
  `claude -p --agent deck-builder-agent --allowedTools mcp__deck-builder "<test prompt>"`.
- Skills hold no engine logic. When a skill needs something the CLI can't do, tell the user;
  building it under `src/` is a separate task, done only when the user asks, with tests.
- Example content uses invented companies only.
