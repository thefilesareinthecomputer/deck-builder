"""deck.xlsx -> Deck. Built in phase 5; see SPEC section 7.2."""
from __future__ import annotations

from pathlib import Path

from deck_builder.errors import EnvError, Issue
from deck_builder.model import Deck


def parse(path: Path, row: dict[str, str] | None = None) -> tuple[Deck, list[Issue]]:
    raise EnvError("workbook input isn't built yet in this version", code="NOT_IMPLEMENTED")
