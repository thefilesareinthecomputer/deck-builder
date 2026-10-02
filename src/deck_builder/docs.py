"""Reference topics shipped with the engine, printed by `deck-builder docs <topic>`.

The topics live in the package so the docs always match the installed engine version.
Skills point at these topics instead of copying them.
"""
from __future__ import annotations

from importlib import resources

from deck_builder.errors import CODES, EnvError

_DIR = "reference"


def _files() -> dict[str, str]:
    root = resources.files("deck_builder").joinpath(_DIR)
    return {p.name[:-3]: p.read_text(encoding="utf-8") for p in root.iterdir() if p.name.endswith(".md")}


def topics() -> dict[str, str]:
    """Topic name -> its first line, without the heading marker."""
    out = {name: text.splitlines()[0].lstrip("# ").strip() for name, text in sorted(_files().items())}
    out["codes"] = "Every issue code with its cause and fix"
    return dict(sorted(out.items()))


def codes_markdown() -> str:
    lines = [
        "# Issue codes",
        "",
        "Generated from the engine by `deck-builder docs codes`. Fix by code, not by message text.",
        "",
        "| Code | Cause | Fix |",
        "|---|---|---|",
    ]
    lines += [f"| `{code}` | {cause} | {fix} |" for code, (cause, fix) in CODES.items()]
    return "\n".join(lines) + "\n"


def read(topic: str) -> str:
    if topic == "codes":
        return codes_markdown()
    files = _files()
    if topic not in files:
        raise EnvError(f"unknown docs topic {topic!r}; topics: {', '.join(topics())}")
    return files[topic]
