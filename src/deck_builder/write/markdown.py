"""Deck -> canonical deck.md. Writing, parsing and writing again gives the same bytes."""
from __future__ import annotations

from typing import Any

import yaml

from deck_builder.model import Chart, Deck, Image, Table, Value
from deck_builder.parse.markdown import FIELD_LINE, STRUCTURE
from deck_builder.write.cells import bullets_text

FRONT_ORDER = ("spec_version", "brand", "title", "author", "date", "default_layout", "slide_level", "template",
               "tokens", "output")


def _dump(data: Any) -> str:
    """Block style at the top level, flow style for lists of scalars (chart categories and values)."""
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=10_000, default_flow_style=None)


def _line(key: str, value: Any) -> str:
    """One `key: value` field line."""
    return yaml.safe_dump({key: value}, sort_keys=False, allow_unicode=True, width=10_000,
                          default_flow_style=False).rstrip("\n")


def front_matter(meta: dict[str, Any]) -> str:
    ordered = {k: meta[k] for k in FRONT_ORDER if k in meta}
    ordered.update({k: meta[k] for k in sorted(meta) if k not in ordered})
    lines = "".join(_line(k, v) + "\n" for k, v in ordered.items())  # one key per line, as people write it
    return f"---\n{lines}---\n"


def _pipe_ok(t: Table) -> bool:
    cells = [*t.header, *(c for r in t.rows for c in r)]
    if any("|" in c or "\n" in c for c in cells):
        return False
    return all(any(c.strip() for c in row) for row in [t.header, *t.rows])


def table_md(t: Table) -> str:
    if not _pipe_ok(t):
        return f"```table\n{_dump({'header': t.header, 'rows': t.rows})}```"
    lines = ["| " + " | ".join(t.header) + " |", "|" + "---|" * len(t.header)]
    lines += ["| " + " | ".join(r) + " |" for r in t.rows]
    return "\n".join(lines)


def chart_spec(c: Chart) -> dict[str, Any]:
    spec: dict[str, Any] = {"type": c.type}
    if c.number_format != "General":
        spec["number_format"] = c.number_format
    if c.labels:
        spec["labels"] = True
    if c.legend is not None:
        spec["legend"] = c.legend
    if c.title:
        spec["title"] = c.title
    if c.colors:
        spec["colors"] = c.colors
    spec["categories"] = c.categories
    spec["series"] = [{"name": s.name, "values": s.values} for s in c.series]
    return spec


def chart_md(c: Chart) -> str:
    return f"```chart\n{_dump(chart_spec(c))}```"


def section_md(value: Value) -> str:
    if isinstance(value, Table):
        return table_md(value)
    if isinstance(value, Chart):
        return chart_md(value)
    if isinstance(value, Image):
        return f"![{value.alt}]({value.ref})"
    if isinstance(value, list):
        return bullets_text(value)
    return str(value)


def _is_line_field(name: str, value: Value) -> bool:
    return isinstance(value, str) and "\n" not in value and bool(FIELD_LINE.match(f"{name}: "))


def _protect_notes(notes: str) -> str:
    """Escape any notes line the parser would read as a heading, image, fence or notes marker, and any
    line that already starts with the escape character, so write then parse gives back the same notes
    text instead of a line like `## Appendix` becoming a new slide. parse.markdown undoes this."""
    return "\n".join(("\\" + ln) if ln.startswith("\\") or STRUCTURE.match(ln) else ln
                     for ln in notes.split("\n"))


def write(deck: Deck) -> str:
    level = int(deck.meta.get("slide_level", 2))
    out = [front_matter(deck.meta)]
    for s in deck.slides:
        block = [f"{'#' * level} {s.title}", _line("layout", s.layout)]
        sections = []
        for name, value in s.fields.items():
            if _is_line_field(name, value):
                block.append(_line(name, value))
            else:
                sections += ["", f"{'#' * (level + 1)} {name}", section_md(value)]
        block += sections
        if s.notes:
            block += ["", "Notes:", _protect_notes(s.notes)]
        out.append("\n" + "\n".join(block) + "\n")
    return "".join(out)
