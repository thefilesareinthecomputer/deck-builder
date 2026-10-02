"""slides.csv -> Deck. The CSV form of the workbook's `slides` sheet; no chart or table sheets."""
from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

from deck_builder.errors import Issue
from deck_builder.model import Deck, Image, Slide, Value, Where
from deck_builder.parse.markdown import BULLET, IMAGE, parse_text_block

SheetResolver = Callable[[str], Value | None]


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


def slides_from_rows(rows: list[tuple[int, dict[str, str]]], file: str, issues: list[Issue],
                     sheet_resolver: SheetResolver | None = None) -> list[Slide]:
    """rows are (row number, cells). Without a resolver (CSV), sheet: references are an error."""
    slides = []
    for n, row in rows:
        where = Where(file=file, line=n)
        cells = {k: v for k, v in row.items() if not k.startswith("#")}
        layout = cells.pop("layout", "").strip()
        title = cells.pop("title", "").strip()
        notes = cells.pop("notes", "").replace("\r\n", "\n").strip()
        cells.pop("slide", None)
        s = Slide(title=title, layout=layout, notes=notes, where=where)
        for k, raw in cells.items():
            ref = raw.strip()
            if ref.startswith("sheet:"):
                if sheet_resolver is None:
                    issues.append(Issue("CSV_NO_SHEETS", f"{ref!r}: CSV can't hold chart or table sheets",
                                        file=file, line=n, field=k))
                    continue
                val = sheet_resolver(ref)
                if val is None:
                    issues.append(Issue("PARSE", f"{ref!r}: no such sheet", file=file, line=n, field=k))
                    continue
                s.fields[k] = val
                continue
            parsed = cell_value(raw)
            if parsed is not None:
                s.fields[k] = parsed
        slides.append(s)
    return slides


def parse(path: Path) -> tuple[Deck, list[Issue]]:
    issues: list[Issue] = []
    rows = list(enumerate(read_rows(path), start=2))
    slides = slides_from_rows(rows, path.name, issues)
    if not slides:
        issues.append(Issue("PARSE", "no rows", file=path.name))
    return Deck(meta={}, slides=slides, source=str(path)), issues
