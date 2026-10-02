"""deck.md -> Deck. See `deck-builder docs deck-md` for the format."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from deck_builder.errors import Issue
from deck_builder.model import Bullets, Chart, Deck, Image, Series, Slide, Table, Value, Where

SPEC_VERSION = 1
FIELD_LINE = re.compile(r"^([a-z_][\w-]*):(\s|$)")
FENCE = re.compile(r"^```(\w+)?\s*$")
IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
NUMBERED = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
TOKEN = re.compile(r"\{\{\s*([\w.-]+)\s*\}\}")
NOTES = re.compile(r"^(Notes|\?\?\?):?\s*$")
STRAY_HEADING = re.compile(r"^#{1,6}\s")
# A line that changes a deck's structure: a heading, an image, a fence, or the start of speaker notes.
STRUCTURE = re.compile(r"^\s*(#|!\[|```|(Notes|\?\?\?):?\s*$)")


def _unescape_notes_line(ln: str) -> str:
    """Undo write.markdown's `_protect_notes`: a leading backslash there always means this line was
    escaped (either it matched STRUCTURE, or it already started with a backslash), so stripping exactly
    one restores the original, whatever it was."""
    return ln[1:] if ln.startswith("\\") else ln


def substitute(text: str, row: dict[str, str] | None, file: str, issues: list[Issue]) -> str:
    """Bulk mode: replace {{column}} tokens from a data row."""
    if row is None:
        return text

    def rep(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in row:
            issues.append(Issue("UNKNOWN_TOKEN", f"{{{{{key}}}}} has no data column", file=file))
            return m.group(0)
        value = str(row[key])
        if len(f"x{value}x".splitlines()) > 1:  # any break splitlines() honors: \v, \f, \x85, U+2028...
            issues.append(Issue("BAD_DATA_VALUE", f"column {key!r} holds a line break", file=file))
        return value

    lines = []
    for line in text.split("\n"):  # values hold no line breaks, so template lines map one to one
        filled = TOKEN.sub(rep, line)
        # judge the filled line, not each value: "{{a}}{{b}}" with an empty a still starts with b
        if filled != line and STRUCTURE.match(filled) and not STRUCTURE.match(TOKEN.sub("x", line)):
            cols = ", ".join(repr(k) for k in TOKEN.findall(line))
            issues.append(Issue("BAD_DATA_VALUE", f"column {cols} would start a heading or image line: "
                                f"{filled.strip()[:40]!r}", file=file))
        lines.append(filled)
    return "\n".join(lines)


def split_front_matter(text: str, file: str, issues: list[Issue]) -> tuple[dict[str, Any], str, int]:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            try:
                meta = yaml.safe_load(text[4:end]) or {}
            except yaml.YAMLError as e:
                issues.append(Issue("PARSE", f"front matter: {e}", file=file, line=1))
                meta = {}
            if not isinstance(meta, dict):
                issues.append(Issue("PARSE", "front matter must be key: value pairs", file=file, line=1))
                meta = {}
            return meta, text[end + 5 :], text[: end + 5].count("\n")
    return {}, text, 0


def parse_text_block(lines: list[str]) -> str | Bullets:
    """One paragraph becomes a string; anything with list markers becomes bullets."""
    items: Bullets = []
    para: list[str] = []
    listed = False
    for ln in lines:
        m = BULLET.match(ln) or NUMBERED.match(ln)
        if m:
            listed = True
            if para:
                items.append((0, " ".join(para)))
                para = []
            items.append((len(m.group(1).expandtabs(2)) // 2, m.group(2).strip()))
        elif ln.strip():
            para.append(ln.strip())
        elif para:
            items.append((0, " ".join(para)))
            para = []
    if para:
        items.append((0, " ".join(para)))
    if len(items) == 1 and not listed:
        return items[0][1]
    return items


def parse_pipe_table(lines: list[str]) -> Table:
    rows = []
    for ln in lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return Table(header=rows[0] if rows else [], rows=rows[1:])


def number(v: Any) -> Any:
    """Whole floats become ints, so 9800 and 9800.0 compare equal across formats."""
    return int(v) if isinstance(v, float) and v.is_integer() else v


def chart_from_spec(spec: dict[str, Any]) -> Chart:
    series = []
    for s in spec.get("series") or []:
        if isinstance(s, dict):
            series.append(Series(name=str(s.get("name", "")), values=[number(v) for v in s.get("values") or []]))
    colors = spec.get("colors")
    return Chart(
        type=str(spec.get("type", "column")),
        categories=[str(c) for c in spec.get("categories") or []],
        series=series,
        number_format=str(spec.get("number_format", "General")),
        labels=bool(spec.get("labels", False)),
        legend=spec.get("legend"),
        title=spec.get("title"),
        colors=[str(c) for c in colors] if colors else None,
    )


def table_from_spec(spec: dict[str, Any]) -> Table:
    return Table(
        header=[str(h) for h in spec.get("header") or []],
        rows=[[str(c) for c in r] for r in spec.get("rows") or []],
    )


def parse_section(lines: list[str], where: Where, label: str, issues: list[Issue]) -> Value | None:
    """The body of a slide, or of a `### field` section: text, or exactly one visual."""
    visuals: list[Value] = []
    text_lines: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        fm = FENCE.match(ln)
        if fm and fm.group(1) in ("chart", "table"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            if j >= len(lines):
                issues.append(Issue("PARSE", f"{label}: unclosed ```{fm.group(1)} block", **_at(where)))
                return None
            try:
                spec = yaml.safe_load("\n".join(lines[i + 1 : j])) or {}
            except yaml.YAMLError as e:
                issues.append(Issue("PARSE", f"{label}: bad YAML in ```{fm.group(1)} block: {e}", **_at(where)))
                spec = {}
            if not isinstance(spec, dict):
                spec = {}
            visuals.append(chart_from_spec(spec) if fm.group(1) == "chart" else table_from_spec(spec))
            i = j + 1
            continue
        if ln.lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            visuals.append(parse_pipe_table(lines[i:j]))
            i = j
            continue
        im = IMAGE.match(ln.strip())
        if im:
            visuals.append(Image(ref=im.group(2).strip(), alt=im.group(1)))
            i += 1
            continue
        text_lines.append(ln)
        i += 1

    has_text = any(ln.strip() for ln in text_lines)
    if visuals and has_text:
        issues.append(Issue("PARSE", f"{label}: holds both text and a visual; give the text its own field",
                            **_at(where)))
        return None
    if len(visuals) > 1:
        issues.append(Issue("PARSE", f"{label}: more than one visual; use separate `### field` sections",
                            **_at(where)))
        return None
    if visuals:
        return visuals[0]
    return parse_text_block(text_lines) if has_text else None


def _at(where: Where) -> dict[str, Any]:
    return {"file": where.file, "line": where.line}


def _scalar_field(v: Any) -> Value:
    if isinstance(v, list):
        return [(0, str(x)) for x in v]
    return "" if v is None else str(v)


def parse(path: Path, row: dict[str, str] | None = None) -> tuple[Deck, list[Issue]]:
    """deck.md -> Deck. With a bulk data row, its {{tokens}} are substituted first."""
    issues: list[Issue] = []
    name = path.name
    raw = substitute(path.read_text(encoding="utf-8"), row, name, issues)
    if issues:  # an unknown token or an unsafe data value: anything parsed past it would be noise
        return Deck(meta={}, slides=[], source=str(path)), issues
    meta, body, offset = split_front_matter(raw, name, issues)
    sv = meta.get("spec_version", SPEC_VERSION)
    if isinstance(sv, int) and sv > SPEC_VERSION:
        issues.append(Issue("SPEC_VERSION", f"spec_version {sv}; this engine supports {SPEC_VERSION}",
                            file=name, line=1, actual=sv, limit=SPEC_VERSION))
    level = int(meta.get("slide_level", 2))
    head = re.compile(r"^" + "#" * level + r"\s+(.*)$")
    sub = re.compile(r"^" + "#" * (level + 1) + r"\s+([\w-]+)\s*$")

    blocks: list[tuple[int, str, list[str]]] = []
    in_fence = False
    for n, ln in enumerate(body.splitlines(), start=offset + 1):
        if ln.startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else head.match(ln)
        if m:
            blocks.append((n, m.group(1).strip(), []))
        elif blocks:
            blocks[-1][2].append(ln)

    slides: list[Slide] = []
    for lineno, title, lines in blocks:
        where = Where(file=name, line=lineno)
        i = 0
        while i < len(lines) and not lines[i].strip():
            i += 1
        head_lines: list[str] = []
        while i < len(lines) and (FIELD_LINE.match(lines[i]) or (head_lines and lines[i].startswith("  "))):
            head_lines.append(lines[i])
            i += 1
        kv: dict[str, Any] = {}
        if head_lines:
            try:
                loaded = yaml.safe_load("\n".join(head_lines))
                kv = loaded if isinstance(loaded, dict) else {}
            except yaml.YAMLError as e:
                issues.append(Issue("PARSE", f"field lines: {e}", **_at(where)))
        rest = lines[i:]

        notes = ""
        for k, ln in enumerate(rest):
            if NOTES.match(ln.strip()):
                notes = "\n".join(_unescape_notes_line(x) for x in rest[k + 1 :]).strip()
                rest = rest[:k]
                break

        layout = str(kv.pop("layout", meta.get("default_layout", "")) or "")
        slide = Slide(title=title, layout=layout, notes=notes, where=where)
        for key, v in kv.items():
            slide.fields[str(key)] = _scalar_field(v)

        sections: list[tuple[str, list[str]]] = [("body", [])]
        in_fence = False
        for ln in rest:
            if ln.startswith("```"):
                in_fence = not in_fence
            m = None if in_fence else sub.match(ln)
            if m:
                sections.append((m.group(1), []))
                continue
            if not in_fence and STRAY_HEADING.match(ln):
                issues.append(Issue("PARSE", f"{ln.strip()!r} isn't a slide or a field: '{'#' * level} ' starts a "
                                    f"slide, and '{'#' * (level + 1)} name' names a field with no spaces in it",
                                    **_at(where)))
                continue
            sections[-1][1].append(ln)
        for fname, sl in sections:
            val = parse_section(sl, where, fname, issues)
            if val is None:
                continue
            if fname in slide.fields:
                issues.append(Issue("PARSE", f"field {fname!r} set twice", field=fname, **_at(where)))
            slide.fields[fname] = val
        slides.append(slide)

    if not slides:
        issues.append(Issue("PARSE", f"no slides found (expected '{'#' * level} ' headings)", file=name))
    return Deck(meta=meta, slides=slides, source=str(path)), issues
