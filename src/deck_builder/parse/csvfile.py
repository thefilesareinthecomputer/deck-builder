"""slides.csv -> Deck. The CSV form of the workbook's `slides` sheet; no chart or table sheets."""
from __future__ import annotations

import csv
from pathlib import Path

from deck_builder.errors import Issue
from deck_builder.model import Deck, Image, Slide, Value, Where
from deck_builder.parse.markdown import BULLET, IMAGE, parse_text_block


def cell_value(raw: str) -> Value | None:
    """A cell's text -> a model value. Shared by the CSV and workbook parsers."""
    v = raw.replace("\r\n", "\n").strip()
    if not v:
        return None
    im = IMAGE.match(v)
    if im:
        return Image(ref=im.group(2).strip(), alt=im.group(1))
    if "\n" in v or BULLET.match(v):
        return parse_text_block(v.splitlines())
    return v


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{(k or "").strip(): (v or "") for k, v in r.items() if k} for r in csv.DictReader(f)]


def slides_from_rows(rows: list[dict[str, str]], file: str, issues: list[Issue],
                     first_row: int = 2) -> list[Slide]:
    slides = []
    for n, row in enumerate(rows, start=first_row):
        where = Where(file=file, line=n)
        cells = {k: v for k, v in row.items() if not k.startswith("#")}
        layout = cells.pop("layout", "").strip()
        title = cells.pop("title", "").strip()
        notes = cells.pop("notes", "").strip()
        cells.pop("slide", None)
        s = Slide(title=title, layout=layout, notes=notes, where=where)
        for k, raw in cells.items():
            if raw.strip().startswith("sheet:"):
                issues.append(Issue("CSV_NO_SHEETS", f"{raw.strip()!r}: CSV can't hold chart or table sheets",
                                    file=file, line=n, field=k))
                continue
            val = cell_value(raw)
            if val is not None:
                s.fields[k] = val
        slides.append(s)
    return slides


def parse(path: Path) -> tuple[Deck, list[Issue]]:
    issues: list[Issue] = []
    slides = slides_from_rows(read_rows(path), path.name, issues)
    if not slides:
        issues.append(Issue("PARSE", "no rows", file=path.name))
    return Deck(meta={}, slides=slides, source=str(path)), issues
