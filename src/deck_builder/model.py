"""The slide model every input format parses into and every writer serializes from."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Bullets = list[tuple[int, str]]  # (nesting level, text)


@dataclass
class Table:
    header: list[str]
    rows: list[list[str]]


@dataclass
class Series:
    name: str
    values: list[Any]  # numbers; anything else is kept so check can report CHART_SHAPE


@dataclass
class Chart:
    type: str = "column"
    categories: list[str] = field(default_factory=list)
    series: list[Series] = field(default_factory=list)
    number_format: str = "General"
    labels: bool = False
    legend: bool | None = None  # None: on for pie charts and for two or more series
    title: str | None = None
    colors: list[str] | None = None


@dataclass
class Image:
    ref: str  # as written: a relative path, or brand:logo/<id>
    alt: str = ""


@dataclass
class Icon:
    ref: str  # brand:icon/<id>


@dataclass
class Code:
    """A fenced code block: highlighted by language, never wrapped, kept as editable text."""

    language: str  # the fence's language tag; "" for plain text
    text: str  # tabs expanded to four spaces, trailing spaces and blank edge lines trimmed
    highlight: list[int] = field(default_factory=list)  # 1-based lines to mark, from `{3,5-7}`
    numbers: bool = False  # line numbers, from `lines`
    title: str | None = None  # a filename line above the code, from `title="etl.py"`

    @property
    def lines(self) -> list[str]:
        return self.text.split("\n")


Value = str | Bullets | Table | Chart | Image | Icon | Code


@dataclass
class Where:
    """Where a slide came from, for issue reports. Not part of model equality."""

    file: str
    line: int | None = None


@dataclass
class Slide:
    title: str
    layout: str
    fields: dict[str, Value] = field(default_factory=dict)
    notes: str = ""
    where: Where | None = field(default=None, compare=False)


@dataclass
class Deck:
    meta: dict[str, Any]
    slides: list[Slide]
    source: str | None = field(default=None, compare=False)


def kind_of(value: Value) -> str:
    if isinstance(value, Table):
        return "table"
    if isinstance(value, Chart):
        return "chart"
    if isinstance(value, Image):
        return "image"
    if isinstance(value, Icon):
        return "icon"
    if isinstance(value, Code):
        return "code"
    if isinstance(value, list):
        return "bullets"
    return "text"
