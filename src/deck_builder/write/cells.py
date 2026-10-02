"""Model values as cell text, shared by the workbook and CSV writers."""
from __future__ import annotations

from deck_builder.model import Bullets, Image, Value


def bullets_text(items: Bullets) -> str:
    return "\n".join(f"{'  ' * lvl}- {text}" for lvl, text in items)


def cell_text(value: Value) -> str:
    """Text, bullets and images as cell text. Charts and tables go to their own sheets."""
    if isinstance(value, list):
        return bullets_text(value)
    if isinstance(value, Image):
        return f"![{value.alt}]({value.ref})"
    return str(value)
