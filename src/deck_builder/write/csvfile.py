"""Deck -> slides.csv, for text-only decks without front matter. Anything else is refused as lossy."""
from __future__ import annotations

import csv
import io

from deck_builder.model import Chart, Deck, Table
from deck_builder.write.cells import cell_text


def lossy_reasons(deck: Deck) -> list[str]:
    reasons = []
    if deck.meta:
        reasons.append(f"CSV has no place for front matter ({', '.join(deck.meta)})")
    for n, s in enumerate(deck.slides, start=1):
        for k, v in s.fields.items():
            if isinstance(v, Chart | Table):
                reasons.append(f"slide {n} field {k!r} is a {'chart' if isinstance(v, Chart) else 'table'}")
    return reasons


def write(deck: Deck) -> str:
    fields: list[str] = []
    for s in deck.slides:
        fields += [k for k in s.fields if k not in fields]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["slide", "layout", "title", *fields, "notes"])
    for n, s in enumerate(deck.slides, start=1):
        w.writerow([n, s.layout, s.title, *(cell_text(s.fields[f]) if f in s.fields else "" for f in fields),
                    s.notes])
    return buf.getvalue()
