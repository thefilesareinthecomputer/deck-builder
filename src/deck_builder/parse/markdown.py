"""deck.md -> Deck. See `deck-builder docs deck-md` for the format."""
from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import yaml

from deck_builder.errors import Issue
from deck_builder.model import Bullets, Chart, Code, Deck, Image, Series, Slide, Table, Value, Where

SPEC_VERSION = 1
FIELD_LINE = re.compile(r"^([a-z_][\w-]*):(\s|$)")
FENCE = re.compile(r"^(`{3,}|~{3,})(.*)$")
HIGHLIGHT = re.compile(r"^\{(\d{1,6}(?:-\d{1,6})?(?:,\d{1,6}(?:-\d{1,6})?)*)\}$")
TAB = 4  # spaces a tab in a code block becomes
IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
IMAGE_FIELD_LINE = re.compile(r"^([a-z_][\w-]*):\s*!\[")  # YAML reads the ! as a tag, so this can't parse
BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
NUMBERED = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
TOKEN = re.compile(r"\{\{\s*([\w.-]+)\s*\}\}")
NOTES = re.compile(r"^(Notes|\?\?\?):?\s*$")
STRAY_HEADING = re.compile(r"^#{1,6}\s")
# A line that changes a deck's structure: a heading, an image, a fence, a field line, a pipe-table row,
# or the start of speaker notes.
STRUCTURE = re.compile(r"^\s*(#|!\[|```|~~~|\||(?:[a-z_][\w-]*:(?:\s|$))|(Notes|\?\?\?):?\s*$)")


def fence_open(ln: str) -> tuple[str, str] | None:
    """(fence, info string) when ln opens a fenced block: three or more backticks or tildes at the start
    of the line. A backtick fence's info string can't hold a backtick (CommonMark)."""
    m = FENCE.match(ln)
    if not m:
        return None
    fence, info = m.group(1), m.group(2).strip()
    if fence[0] == "`" and "`" in info:
        return None
    return fence, info


def fence_closes(ln: str, fence: str) -> bool:
    """ln closes a block opened with fence: the same character at least as many times, and nothing else.
    So a four-backtick block can hold a three-backtick fence, and a tilde block a backtick one."""
    s = ln.rstrip()
    return len(s) >= len(fence) and set(s) == {fence[0]}


def fence_state(fence: str | None, ln: str) -> str | None:
    """The fence still open after line ln, or None outside a block."""
    if fence is None:
        opened = fence_open(ln)
        return opened[0] if opened else None
    return None if fence_closes(ln, fence) else fence


def code_from_fence(info: str, body: list[str]) -> tuple[Code | None, str | None]:
    """A fenced block's info string and lines -> (Code, None), (None, None) when it holds no code, or
    (None, why it's wrong). The info string is the language, then any of `{3,5-7}` (lines to highlight),
    `lines` (line numbers) and `title="etl.py"` (a filename line)."""
    info = re.sub(r"\{[^}]*\}", lambda m: m.group(0).replace(" ", ""), info)  # `{3, 5-7}` reads as one option
    try:
        words = shlex.split(info)
    except ValueError as e:
        return None, f"can't read the options {info!r}: {e}"
    language = ""
    if words and not words[0].startswith("{") and "=" not in words[0] and words[0] != "lines":
        language = words.pop(0)
    text = "\n".join(ln.expandtabs(TAB).rstrip() for ln in body).strip("\n")
    if not text.strip():
        return None, None
    code = Code(language=language, text=text)
    n = len(code.lines)
    for w in words:
        hl = HIGHLIGHT.match(w)
        if w == "lines":
            code.numbers = True
        elif w.startswith("title="):
            code.title = w[len("title="):] or None
        elif hl:
            picked: set[int] = set()
            for part in hl.group(1).split(","):
                a, _, b = part.partition("-")
                first, last = int(a), int(b or a)
                if not 1 <= first <= last <= n:  # checked before expanding, so a range can't run to millions
                    bad = first if not 1 <= first <= n else last
                    return None, f"highlights line {bad}, and the block has {n} line{'s' * (n != 1)}"
                picked.update(range(first, last + 1))
            code.highlight = sorted(picked)
        else:
            return None, (f"unknown option {w!r} after the language; a code fence takes `{{3,5-7}}`, `lines` "
                          'and `title="name"`')
    return code, None


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
        opened = fence_open(ln)
        if opened:
            fence, info = opened
            head = f"{fence}{info.split()[0] if info else ''}"
            j = i + 1
            while j < len(lines) and not fence_closes(lines[j], fence):
                j += 1
            if j >= len(lines):
                issues.append(Issue("PARSE", f"{label}: unclosed {head} block", **_at(where)))
                return None
            kind = info.split()[0] if info else ""
            if kind in ("chart", "table"):
                try:
                    spec = yaml.safe_load("\n".join(lines[i + 1 : j])) or {}
                except yaml.YAMLError as e:
                    issues.append(Issue("PARSE", f"{label}: bad YAML in {head} block: {e}", **_at(where)))
                    spec = {}
                if not isinstance(spec, dict):
                    spec = {}
                visuals.append(chart_from_spec(spec) if kind == "chart" else table_from_spec(spec))
            else:
                code, why = code_from_fence(info, lines[i + 1 : j])
                if why:
                    issues.append(Issue("PARSE", f"{label}: {head} block: {why}", **_at(where)))
                    return None
                if code is not None:
                    visuals.append(code)
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
    raw_level = meta.get("slide_level", 2)
    try:
        level = int(raw_level)
        if isinstance(raw_level, bool) or not 1 <= level <= 6:
            raise ValueError
    except (TypeError, ValueError):
        issues.append(Issue("PARSE", f"front matter slide_level: {raw_level!r} must be a whole number from "
                            "1 to 6; using 2 to keep reading", file=name, line=1))
        level = 2
    head = re.compile(r"^" + "#" * level + r"\s+(.*)$")
    sub = re.compile(r"^" + "#" * (level + 1) + r"\s+([\w-]+)\s*$")

    blocks: list[tuple[int, str, list[str]]] = []
    fence: str | None = None
    for n, ln in enumerate(body.splitlines(), start=offset + 1):
        fence = fence_state(fence, ln)
        m = None if fence else head.match(ln)
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
                image = next((m.group(1) for ln in head_lines if (m := IMAGE_FIELD_LINE.match(ln))), None)
                hint = (f"; an image goes in a `### {image}` section holding the ![alt](path) line, not on a "
                        "field line" if image else "")
                issues.append(Issue("PARSE", f"field lines: {e}{hint}", **_at(where)))
        rest = lines[i:]

        notes = ""
        fence = None
        for k, ln in enumerate(rest):
            fence = fence_state(fence, ln)
            if not fence and NOTES.match(ln.strip()):  # a `Notes:` line inside a code block is code
                notes = "\n".join(_unescape_notes_line(x) for x in rest[k + 1 :]).strip()
                rest = rest[:k]
                break

        layout = str(kv.pop("layout", meta.get("default_layout", "")) or "")
        slide = Slide(title=title, layout=layout, notes=notes, where=where, current=kv.pop("current", None))
        for key, v in kv.items():
            slide.fields[str(key)] = _scalar_field(v)

        sections: list[tuple[str, list[str]]] = [("body", [])]
        fence = None
        for ln in rest:
            fence = fence_state(fence, ln)
            m = None if fence else sub.match(ln)
            if m:
                sections.append((m.group(1), []))
                continue
            if not fence and STRAY_HEADING.match(ln):
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
