"""`skills install`: link this clone's skills and agent into another Claude Code setup.

Links, never copies, so a `git pull` in the clone updates every repo that uses them. Changes nothing
without --yes, and never replaces an existing file or folder.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from deck_builder.errors import EnvError

SKILLS = ("deck-builder", "deck-brand", "deck-onboard")
AGENTS = ("deck-builder-agent.md", "deck-brand-agent.md", "deck-decomposer-agent.md")


@dataclass
class Link:
    source: Path
    target: Path
    status: str  # create | linked | conflict


def find_clone(start: Path) -> Path:
    """The clone above start, else the clone this engine runs from (an editable install or `uv run --project`)."""
    for d in [start, *start.parents, Path(__file__).resolve().parents[2]]:
        if (d / ".claude" / "skills" / "deck-builder" / "SKILL.md").is_file():
            return d
    raise EnvError("run this from inside a deck-builder clone; its .claude/ folder holds the skills to link")


def plan(clone: Path, target: Path) -> list[Link]:
    links = []
    pairs = [(clone / ".claude" / "skills" / s, target / "skills" / s) for s in SKILLS]
    pairs += [(clone / ".claude" / "agents" / a, target / "agents" / a) for a in AGENTS]
    for src, dst in pairs:
        if dst.is_symlink() and dst.resolve() == src.resolve():
            status = "linked"
        elif dst.exists() or dst.is_symlink():
            status = "conflict"
        else:
            status = "create"
        links.append(Link(src, dst, status))
    return links


def apply(links: list[Link]) -> None:
    for link in links:
        if link.status == "create":
            link.target.parent.mkdir(parents=True, exist_ok=True)
            link.target.symlink_to(link.source, target_is_directory=link.source.is_dir())
            link.status = "linked"
