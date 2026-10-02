"""Load a deck from any supported format and resolve its brand. Shared by check, build and convert."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from deck_builder import config as cfgmod
from deck_builder.brand import registry
from deck_builder.brand.registry import Brand
from deck_builder.errors import EnvError, Issue
from deck_builder.model import Deck
from deck_builder.parse import csvfile, markdown

FORMATS = {".md": "markdown", ".markdown": "markdown", ".csv": "csv", ".xlsx": "workbook"}


@dataclass
class Loaded:
    path: Path
    deck: Deck
    issues: list[Issue]


def load_deck(path: Path, row: dict[str, str] | None = None) -> Loaded:
    if not path.is_file():
        raise EnvError(f"deck not found: {path}")
    fmt = FORMATS.get(path.suffix.lower())
    if fmt == "markdown":
        deck, issues = markdown.parse(path, row)
    elif fmt == "csv":
        deck, issues = csvfile.parse(path)
    elif fmt == "workbook":
        from deck_builder.parse import workbook

        deck, issues = workbook.parse(path, row)
    else:
        raise EnvError(f"unsupported input {path.suffix!r}; use .md, .xlsx or .csv")
    return Loaded(path=path, deck=deck, issues=issues)


def brand_for(deck: Deck, deck_path: Path, cfg: cfgmod.Config, override: str | None = None) -> Brand:
    """Explicit template+tokens in the deck win; then --brand; then the deck's brand; then the default."""
    meta = deck.meta
    base = deck_path.parent
    if meta.get("template") and meta.get("tokens"):
        return registry.explicit(base / str(meta["template"]), base / str(meta["tokens"]))
    slug = override or meta.get("brand") or cfg.default_brand
    if not slug:
        raise EnvError("no brand: set `brand:` in the deck, pass --brand, or set default_brand in config",
                       code="UNKNOWN_BRAND")
    return registry.get(cfg, str(slug))
