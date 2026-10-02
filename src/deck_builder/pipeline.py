"""Load a deck from any supported format and resolve its brand. Shared by check, build and convert."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from deck_builder import config as cfgmod
from deck_builder import confine
from deck_builder.brand import registry
from deck_builder.brand.registry import Brand
from deck_builder.errors import EnvError, Issue
from deck_builder.model import Deck
from deck_builder.parse import csvfile, markdown, workbook

FORMATS = {".md": "markdown", ".markdown": "markdown", ".csv": "csv", ".xlsx": "workbook"}


@dataclass
class Loaded:
    path: Path
    deck: Deck
    issues: list[Issue]


DECK_FILES = ("deck.md", "deck.xlsx", "deck.csv")


def deck_path(path: Path) -> Path:
    """A deck file as given, or the deck file inside a deck folder."""
    if path.is_dir():
        found = [path / name for name in DECK_FILES if (path / name).is_file()]
        if len(found) > 1:
            raise EnvError(f"{path} has more than one deck file ({', '.join(p.name for p in found)}); "
                           "pass the deck file itself, or remove the extra copy", code="AMBIGUOUS_DECK")
        if found:
            # the folder argument was already checked; the file found inside it can still be an
            # existing symlink pointing outside, so confine it here too (a no-op outside MCP).
            return confine.guard(found[0], "the deck file")
        raise EnvError(f"no {', '.join(DECK_FILES)} in {path}; pass the deck file itself")
    if not path.is_file():
        raise EnvError(f"deck not found: {path}")
    return path


def load_deck(path: Path, row: dict[str, str] | None = None) -> Loaded:
    path = deck_path(path)
    fmt = FORMATS.get(path.suffix.lower())
    if fmt == "markdown":
        deck, issues = markdown.parse(path, row)
    elif fmt == "csv":
        deck, issues = csvfile.parse(path)
    elif fmt == "workbook":
        deck, issues = workbook.parse(path, row)
    else:
        raise EnvError(f"unsupported input {path.suffix!r}; use .md, .xlsx or .csv")
    return Loaded(path=path, deck=deck, issues=issues)


def content_sha(deck: Deck) -> str:
    """A hash of the deck's content, the same whichever format it was written in: its canonical markdown."""
    from deck_builder.write import markdown as md_writer

    return hashlib.sha256(md_writer.write(deck).encode("utf-8")).hexdigest()


def brand_for(deck: Deck, deck_path: Path, cfg: cfgmod.Config, override: str | None = None) -> Brand:
    """Explicit template+tokens in the deck win; then --brand; then the deck's brand; then the default."""
    meta = deck.meta
    base = deck_path.parent
    if meta.get("template") and meta.get("tokens"):
        paths = [base / str(meta[k]) for k in ("template", "tokens")]
        if not all(p.resolve().is_relative_to(base.resolve()) for p in paths):  # like images: no reaching out
            raise EnvError("front matter template: and tokens: must be files inside the deck's folder")
        return registry.explicit(*paths)
    slug = override or meta.get("brand") or cfg.default_brand
    if not slug:
        raise EnvError("no brand: set `brand:` in the deck, pass --brand, or set default_brand in config",
                       code="UNKNOWN_BRAND")
    return registry.get(cfg, str(slug))
