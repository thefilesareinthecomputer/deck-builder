"""slides.csv -> Deck. The CSV form of the workbook's `slides` sheet; no chart or table sheets."""
from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path
from typing import Any

from deck_builder.errors import EnvError, Issue
from deck_builder.model import SLIDE_KEYS, Deck, Image, Slide, Value, Where
from deck_builder.parse.markdown import BULLET, IMAGE, code_from_fence, fence_closes, fence_open, parse_text_block

SheetResolver = Callable[[str], Value | None]


def cell_value(raw: str) -> Value | None:
    """A cell's text -> a model value. Shared by the CSV and workbook parsers."""
    v = raw.replace("\r\n", "\n").strip()
    if not v:
        return None
    im = IMAGE.match(v)
    if im:
        return Image(ref=im.group(2).strip(), alt=im.group(1))
    lines = v.split("\n")
    opened = fence_open(lines[0])
    if opened and len(lines) > 1 and fence_closes(lines[-1], opened[0]):  # a fenced code block, whole
        code, _ = code_from_fence(opened[1], lines[1:-1])
        if code is not None:
            return code
    if "\n" in v or BULLET.match(v):
        return parse_text_block(v.splitlines())
    return v


def read_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            return [{(k or "").strip(): (v or "") for k, v in r.items() if k} for r in csv.DictReader(f)]
    except UnicodeDecodeError as e:
        raise EnvError(f"{path} isn't UTF-8 text; in Excel, save it as \"CSV UTF-8\" and try again") from e


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
        settings: dict[str, Any] = {k: cells.pop(k, "").strip() or None for k in SLIDE_KEYS}
        if settings["current"] and settings["current"].isdecimal():
            settings["current"] = int(settings["current"])
        s = Slide(title=title, layout=layout, notes=notes, where=where, **settings)
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
