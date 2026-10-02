# Release checklist

Run in order before tagging. Record the date and the result of each manual step in the release's pull request.

1. `uv run pytest` passes with LibreOffice and poppler installed, so the render tier runs.
2. `uv run ruff check` and `uv run mypy` are clean.
3. CI is green on the release commit: lint, test, audit and render.
4. `docs/issue-codes.md` matches `uv run deck-builder docs codes` (a test enforces this).
5. On a Mac with PowerPoint: `scripts/probe_powerpoint.sh <built example deck>` produces a PDF with the right page count, shows no dialog, and leaves PowerPoint as it found it. Until this passes, the backend stays marked `RENDER_UNVERIFIED`.
6. On a Mac with PowerPoint: open each example deck and a deck from each generated layout set; none shows a repair prompt.
7. Onboarding from a fresh clone on a machine with only LibreOffice and poppler: `uv sync`, `doctor`, `init`, `check --render` on the example deck.
8. `uv tool install` from the tag works, and `deck-builder --version` prints the release version.
9. Bump the version in `pyproject.toml` and `src/deck_builder/__init__.py`, update `CHANGELOG.md`, tag `vX.Y.Z`.
