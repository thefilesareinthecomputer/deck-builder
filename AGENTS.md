# deck-builder

This repo is a PowerPoint deck builder: a deterministic engine (`src/deck_builder/`, the
`deck-builder` CLI) plus a Claude Code layer that drives the same CLI.

## First run

If `uv run deck-builder brand list` reports no config, the user hasn't onboarded yet. Run the
`deck-onboard` skill before anything else.

## Division of labor

- For any request about a deck, a `.pptx` or a brand kit, load the matching skill in the table below
  before you answer or act. The skill has the steps; the rules here are the boundaries.
- The engine parses, converts, validates, builds, renders and measures. It never calls the network.
  Run it first on the files you're given (`check`, or the command the user asked for): when it names
  a problem in a file, its message is the diagnosis, so act on it rather than inspecting the file with
  `file`, `xxd`, `iconv` or the like.
- You write content (`deck.md` or a workbook) and `brand.yaml`, and you judge results.
- You never write python-pptx code or PowerPoint XML for a deck, and never edit a built `.pptx`.
  A deck changes through its source file and a rebuild, which the `deck-builder` skill covers, so
  load it and make the change that way rather than answer with a refusal.
- Brand kits (`brand.yaml`, `tokens.yaml`, templates) change only when the user asks: edit the kit's
  `brand.yaml` or budgets and regenerate with `deck-builder brand` commands, which back the kit up
  first. Never move, copy over or delete a kit folder with shell commands. Styling goes there, never
  into engine code.
- Any edit to a `deck.md` goes through the `deck-builder` skill.
- Delegation threshold: writing or changing 6 or more slides, or any restructure, goes to the
  `deck-builder-agent` subagent; get the user's OK on the storyline at the same threshold. A rebuild
  with no content change (a new or changed brand kit) needs no subagent.
- Every loop stops after two rounds, then you report to the user, so no loop runs unseen: an
  agent's own check-and-fix loop, and the send-backs for one deck or kit (review findings and
  budget tuning counted together). Send work back to the same subagent with SendMessage, so it
  keeps the docs it has read.

| Task | Skill or agent |
|---|---|
| Setup, missing tools, first deck | `deck-onboard` skill |
| Brand kits: the conversation with the user | `deck-brand` skill |
| Brand kits: generating, checking and test-rendering a kit from those decisions | `deck-brand-agent` subagent |
| A deck from a large body of documents, notes or a knowledge base or vault | `deck-decomposer-agent` subagent writes `outline.md` and a draft `deck.md`; the user co-authors and proofreads before anything is built |
| A deck that has to persuade or land harder, or points with no clear arc (optional; also when a subagent's report asks for it) | `deck-storyteller-agent` subagent writes `storyboard.md`: the arc, the title spine and each slide's visual form; the user approves it as the storyline |
| Writing, converting, building, rendering decks | `deck-builder` skill |
| The build loop at or past the delegation threshold above | `deck-builder-agent` subagent, then the review gate in the `deck-builder` skill |
| Final proofread and sign-off of a built deck, before it's called finished | `deck-validator-agent` subagent, run by the main agent at the review gate; its send-backs count toward the two rounds above |

Subagents can't talk with the user. The main agent holds the conversation, hands each agent the
decisions it needs, relays the questions they return, and reviews their work before the user sees it.

The subagents have no shell; put their input files inside the workspace before handing off, since
`deck-builder-agent`, `deck-brand-agent` and `deck-validator-agent` reach the engine only through the
deck-builder MCP server (`deck-builder mcp`, which needs the CLI on PATH), and the decomposer and the
storyteller run no commands at all.
`deck-builder docs agents` maps every CLI command and MCP tool to the one party that owns it, and
says what each subagent may read and write.

## Working on the engine itself

Changes to this repo follow [CONTRIBUTING.md](CONTRIBUTING.md).

- `uv run pytest`, `uv run ruff check`, `uv run mypy` must pass before a commit.
- Example content uses invented companies and people only.
- `tasks/` holds local working notes (the handoff, plans, the archived design spec) and isn't tracked.
- Skills hold no engine logic. When a skill needs something the CLI can't do, tell the user;
  building it under `src/` is a separate task, done only when the user asks, with tests.
