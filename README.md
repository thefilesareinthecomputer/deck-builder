# deck-builder

Build branded, fully editable PowerPoint decks from markdown or spreadsheets, using a real PowerPoint template as the design system.

deck-builder is deterministic: the same input gives the same file, every slide fills a template placeholder, and anything that doesn't fit fails a check instead of being improvised. One CLI serves people and agents. The repo also ships a Claude Code layer (skills and a subagent) that drives that same CLI.

Status: under construction toward v0.1.0. See [SPEC.md](SPEC.md) and [tasks/plan.md](tasks/plan.md).

## Quick start

```bash
uv sync
uv run deck-builder --help
uv run deck-builder docs workflow
```

Opening the repo in Claude Code starts onboarding.

## License

MIT. See [LICENSE](LICENSE).
