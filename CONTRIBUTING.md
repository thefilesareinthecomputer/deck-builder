# Contributing to deck-builder

## Before you start

For anything bigger than a small fix, open an issue first and agree on the change before you build it. [AGENTS.md](AGENTS.md) explains how the engine and the Claude Code layer split the work, and `deck-builder docs agents` maps every CLI command and MCP tool to the party that owns it.

## Setting up

You need Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/thefilesareinthecomputer/deck-builder.git && cd deck-builder
uv sync
uv run pytest
uv run deck-builder doctor
```

The render tier of the tests needs LibreOffice and poppler, and `doctor` tells you if either is missing. To run the tool and the agents' MCP server straight from your clone, install it with `uv tool install --editable .`, and run that again with `--reinstall` after a pull that adds a dependency.

## What every change needs

- A test that fails without the change.
- `uv run pytest`, `uv run ruff check` and `uv run mypy` passing. Run the render tier (`uv run pytest -m render`) too when the change affects how slides look.
- An entry in `CHANGELOG.md` under Unreleased, plus an "Upgrading" note when users have to do something after they update.
- Docs updated wherever behavior changes: the README, the reference topics in `src/deck_builder/reference/` (what `deck-builder docs` prints), and `docs/issue-codes.md`, which must match `uv run deck-builder docs codes` (a test checks).
- For a visual change, the fixture decks in `tests/fixtures/demo-brands/` rendered before and after, with the contact sheets compared. Judge restraint first: nothing should look busier than the feature needs. If the README images change, regenerate them with `uv run python scripts/readme_images.py`.

## How the code stays consistent

- The engine is deterministic, so the same input builds the same bytes. It never calls the network and depends on no model SDK (tests check both).
- Styling lives in brand kits, never in engine code. Only `build/visuals.py` turns tokens into colors and sizes (a test checks).
- Skills and agent prompts hold no engine logic. When a skill needs something the CLI can't do, that's an engine change with its own tests.
- Match the code around your change: its naming, its comment density, and docstrings that say what a thing does and why.
- Make the smallest change that meets the need.

## Agent and skill files

- Agent and skill files load when a Claude Code session starts, so test an edited one in a fresh process: `claude -p "<test prompt>" --agent <name> --allowedTools "<its tools>"`. Put the prompt first, because `--allowedTools` takes a variable number of values and swallows anything after it. Run an agent that uses MCP tools from the repo root, so `deck-builder mcp` finds the clone's `deck-builder.toml`.
- An agent's `tools:` list sets what it's allowed to do. A pull request that changes one says so, and it needs the maintainer's explicit OK.
- Every agent is linked by `skills install`, mapped in `deck-builder docs agents`, and reads `docs design` before it writes or judges slides (a test checks).

## Writing

The writing rules for slides in `deck-builder docs design` apply to docs, comments and commit messages too: plain words, full sentences, American spelling, no em dashes and no teasers. Example content uses invented companies and people only. Keep secrets and machine-specific paths out of code, docs and commit messages. A commit message describes what the change does.

## Commits and pull requests

- Make one logical change per commit.
- A pull request says what changed and why, how you tested it (the commands and their results), and which issue it closes. Add before and after renders for a visual change.
- CI must pass: lint, test, render and audit.
- Releases follow the [release checklist](docs/release-checklist.md).

## Security

Report a vulnerability privately, as [SECURITY.md](SECURITY.md) describes, not in a public issue.

## License

By contributing, you agree that your contributions are released under the [MIT License](LICENSE).
