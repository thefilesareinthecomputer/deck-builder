"""Check a parsed deck against its brand. Collects every issue; never stops at the first.

`resolve` returns a copy of the deck with the heading and body sections mapped onto the layout's
fields and asset references typed, which is what the builder consumes.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from deck_builder import template as tpl
from deck_builder.brand.registry import Brand
from deck_builder.errors import Issue
from deck_builder.model import Chart, Deck, Icon, Image, Slide, Table, Value, kind_of

CHART_TYPES = ("column", "stacked-column", "bar", "stacked-bar", "line", "pie", "doughnut")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
INLINE = [
    (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),
    (re.compile(r"\*(.+?)\*"), r"\1"),
    (re.compile(r"`([^`]+)`"), r"\1"),
]


def plain(text: str) -> str:
    """Text as it will appear on the slide, inline markup removed."""
    for pat, rep in INLINE:
        text = pat.sub(rep, text)
    return text


def text_of(value: Value) -> str:
    if isinstance(value, list):
        return "\n".join(t for _, t in value)
    if isinstance(value, Table):
        return "\n".join([*value.header, *(c for r in value.rows for c in r)])
    if isinstance(value, Chart):
        return "\n".join([value.title or "", *value.categories, *(s.name for s in value.series)])
    if isinstance(value, Image | Icon):
        return ""
    return str(value)


def resolve_asset(ref: str, brand: Brand, deck_dir: Path) -> tuple[Path | None, str | None]:
    """A reference -> (file path, error code or None)."""
    if ref.startswith("brand:logo/"):
        rel = (brand.meta.get("logos") or {}).get(ref.split("/", 1)[1])
        if not rel:
            return None, "UNKNOWN_ASSET"
        return brand.path / str(rel), None
    if ref.startswith("brand:icon/"):
        icons_dir = (brand.meta.get("icons") or {}).get("dir")
        if not icons_dir:
            return None, "UNKNOWN_ASSET"
        p = brand.path / str(icons_dir) / f"{ref.split('/', 1)[1]}.png"
        return (p, None) if p.is_file() else (None, "UNKNOWN_ASSET")
    if ref.startswith("brand:"):
        return None, "UNKNOWN_ASSET"
    p = Path(ref)
    return (p if p.is_absolute() else deck_dir / p), None


def _coerce(value: Value, want: str) -> Value:
    """Field values written as plain text that name an asset become typed values."""
    if isinstance(value, str):
        if want == "icon":
            return Icon(ref=value.strip())
        if want == "image":
            return Image(ref=value.strip())
    return value


def _fits(want: str, got: str, value: Value) -> bool:
    if got == want:
        return True
    if want == "bullets" and got == "text":
        return True
    return want == "text" and got == "bullets" and isinstance(value, list) and len(value) == 1


def resolve(deck: Deck, brand: Brand, deck_dir: Path) -> tuple[Deck, list[Issue]]:
    deck = copy.deepcopy(deck)
    issues: list[Issue] = []
    spec_layouts: dict[str, Any] = brand.tokens.get("layouts") or {}
    lint = brand.meta.get("lint") or {}
    banned = [re.compile(p) for p in lint.get("banned_patterns") or []]

    prs_layouts: dict[Any, Any] = {}
    if brand.template is not None and brand.template.is_file():
        prs_layouts = tpl.layouts(tpl.open_template(brand.template))

    max_slides = lint.get("max_slides")
    if max_slides and len(deck.slides) > max_slides:
        issues.append(Issue("MAX_SLIDES", f"{len(deck.slides)} slides, limit {max_slides}",
                            file=_file(deck), actual=len(deck.slides), limit=max_slides))

    for n, s in enumerate(deck.slides, start=1):
        issues += _check_slide(s, n, spec_layouts, prs_layouts, brand, deck_dir, banned)
    return deck, issues


def _file(deck: Deck) -> str | None:
    return Path(deck.source).name if deck.source else None


def _check_slide(s: Slide, n: int, spec_layouts: dict[str, Any], prs_layouts: dict[Any, Any],
                 brand: Brand, deck_dir: Path, banned: list[re.Pattern[str]]) -> list[Issue]:
    out: list[Issue] = []
    at: dict[str, Any] = {"file": s.where.file if s.where else None,
                          "line": s.where.line if s.where else None, "slide": n}

    if not s.layout:
        out.append(Issue("UNKNOWN_LAYOUT", "no layout: and no default_layout in front matter", **at))
        return out
    ls = spec_layouts.get(s.layout)
    if ls is None:
        known = ", ".join(spec_layouts) or "none"
        out.append(Issue("UNKNOWN_LAYOUT", f"layout {s.layout!r} isn't in the brand (has: {known})", **at))
        return out
    tl = ls.get("template_layout")
    if prs_layouts and tpl.find_layout(prs_layouts, str(tl), ls.get("master")) is None:
        out.append(Issue("TEMPLATE_MISMATCH",
                         f"tokens map {s.layout!r} to template layout {tl!r}, which the template lacks", **at))

    fspecs: dict[str, Any] = ls.get("fields") or {}
    hf = ls.get("heading_field", "title")
    if hf in fspecs and hf not in s.fields and s.title:
        s.fields[hf] = s.title
    if "body" in s.fields and "body" not in fspecs:
        got = kind_of(s.fields["body"])
        accepts = {got, "bullets"} if got == "text" else {got}
        if got == "text":
            accepts |= {"icon", "image"} if str(s.fields["body"]).startswith("brand:") else set()
        cands = [k for k, f in fspecs.items() if f.get("kind", "text") in accepts and k not in s.fields]
        if len(cands) == 1:
            s.fields[cands[0]] = s.fields.pop("body")
        else:
            s.fields.pop("body")
            takes = ", ".join(f"{k} ({f.get('kind', 'text')})" for k, f in fspecs.items())
            reason = "no free field" if not cands else f"several free fields ({', '.join(cands)})"
            out.append(Issue("KIND_MISMATCH",
                             f"the slide body is {got}, and layout {s.layout!r} has {reason} of that kind; "
                             f"it takes: {takes}. Name the field with `### <field>`.", field="body", **at))

    for name in list(s.fields):
        fs = fspecs.get(name)
        if fs is None:
            out.append(Issue("UNKNOWN_FIELD",
                             f"field {name!r} isn't on layout {s.layout!r} (has: {', '.join(fspecs)})",
                             field=name, **at))
            continue
        want = fs.get("kind", "text")
        s.fields[name] = _coerce(s.fields[name], want)
        out += _check_field(name, s.fields[name], fs, want, brand, deck_dir, at)
        txt = plain(text_of(s.fields[name]))
        for pat in banned:
            if pat.search(txt):
                out.append(Issue("BANNED_PATTERN", f"matches {pat.pattern!r}", field=name, **at))
    for pat in banned:
        if s.notes and pat.search(s.notes):
            out.append(Issue("BANNED_PATTERN", f"speaker notes match {pat.pattern!r}", field="notes", **at))
    for name, fs in fspecs.items():
        if fs.get("required") and name not in s.fields:
            out.append(Issue("MISSING_FIELD", f"required field {name!r} is empty", field=name, **at))
    return out


def _check_field(name: str, val: Value, fs: dict[str, Any], want: str, brand: Brand, deck_dir: Path,
                 at: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    got = kind_of(val)
    if not _fits(want, got, val):
        out.append(Issue("KIND_MISMATCH", f"expects {want}, got {got}", field=name, **at))
        return out
    if want in ("text", "bullets"):
        n = len(plain(text_of(val)))
        if fs.get("max_chars") and n > fs["max_chars"]:
            out.append(Issue("BUDGET_CHARS", f"{n} chars, budget {fs['max_chars']}", field=name,
                             actual=n, limit=fs["max_chars"], **at))
    if want == "bullets" and isinstance(val, list) and val:
        if fs.get("max_bullets") and len(val) > fs["max_bullets"]:
            out.append(Issue("BUDGET_BULLETS", f"{len(val)} bullets, budget {fs['max_bullets']}", field=name,
                             actual=len(val), limit=fs["max_bullets"], **at))
        if fs.get("max_bullet_chars"):
            for _, t in val:
                n = len(plain(t))
                if n > fs["max_bullet_chars"]:
                    out.append(Issue("BUDGET_BULLET_CHARS",
                                     f"{n} chars, budget {fs['max_bullet_chars']}: {plain(t)[:40]!r}",
                                     field=name, actual=n, limit=fs["max_bullet_chars"], **at))
        deepest = max(lv for lv, _ in val)
        if deepest > fs.get("max_level", 1):
            out.append(Issue("BUDGET_LEVEL", f"nests to level {deepest}, max {fs.get('max_level', 1)}",
                             field=name, actual=deepest, limit=fs.get("max_level", 1), **at))
    if isinstance(val, Table):
        out += _check_table(name, val, fs, at)
    if isinstance(val, Chart):
        out += _check_chart(name, val, brand, at)
    if isinstance(val, Image | Icon):
        out += _check_asset(name, val.ref, brand, deck_dir, at)
    return out


def _check_table(name: str, t: Table, fs: dict[str, Any], at: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    if not t.header:
        out.append(Issue("TABLE_SHAPE", "no header row", field=name, **at))
    if fs.get("max_rows") and len(t.rows) > fs["max_rows"]:
        out.append(Issue("TABLE_SHAPE", f"{len(t.rows)} rows, limit {fs['max_rows']}", field=name,
                         actual=len(t.rows), limit=fs["max_rows"], **at))
    if fs.get("max_cols") and len(t.header) > fs["max_cols"]:
        out.append(Issue("TABLE_SHAPE", f"{len(t.header)} columns, limit {fs['max_cols']}", field=name,
                         actual=len(t.header), limit=fs["max_cols"], **at))
    if any(len(r) != len(t.header) for r in t.rows):
        out.append(Issue("TABLE_SHAPE", "a row has a different number of cells than the header",
                         field=name, **at))
    return out


def _check_chart(name: str, c: Chart, brand: Brand, at: dict[str, Any]) -> list[Issue]:
    out: list[Issue] = []
    if c.type not in CHART_TYPES:
        out.append(Issue("CHART_SHAPE", f"type {c.type!r}; allowed: {', '.join(CHART_TYPES)}", field=name, **at))
    if not c.categories or not c.series:
        out.append(Issue("CHART_SHAPE", "needs categories and at least one series", field=name, **at))
    for sr in c.series:
        if len(sr.values) != len(c.categories):
            out.append(Issue("CHART_SHAPE",
                             f"series {sr.name!r} has {len(sr.values)} values for {len(c.categories)} categories",
                             field=name, **at))
        if any(not isinstance(v, int | float) or isinstance(v, bool) for v in sr.values):
            out.append(Issue("CHART_SHAPE", f"series {sr.name!r} has a non-numeric value", field=name, **at))
    for col in c.colors or []:
        if brand.color(col) is None:
            out.append(Issue("UNKNOWN_ASSET", f"color {col!r} is neither a palette name nor hex",
                             field=name, **at))
    return out


def _check_asset(name: str, ref: str, brand: Brand, deck_dir: Path, at: dict[str, Any]) -> list[Issue]:
    if re.match(r"^[a-z][a-z0-9+.-]*://", ref, re.IGNORECASE):
        return [Issue("MISSING_IMAGE", f"{ref!r} is a web address; images must be local files, so download it "
                      "into the deck folder and use its path", field=name, **at)]
    path, err = resolve_asset(ref, brand, deck_dir)
    if err:
        return [Issue(err, f"{ref!r} isn't defined in brand {brand.slug!r}", field=name, **at)]
    assert path is not None
    if path.suffix.lower() == ".svg":
        return [Issue("ASSET_FORMAT", f"{ref!r} is SVG; convert it to PNG", field=name, **at)]
    if path.suffix.lower() not in IMAGE_EXT:
        return [Issue("ASSET_FORMAT", f"{ref!r}: unsupported image type {path.suffix}", field=name, **at)]
    if not path.is_file():
        return [Issue("MISSING_IMAGE", f"{ref!r} not found at {path}", field=name, **at)]
    return []
