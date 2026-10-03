"""Check a parsed deck against its brand. Collects every issue; never stops at the first.

`resolve` returns a copy of the deck with the heading and body sections mapped onto the layout's
fields and asset references typed, which is what the builder consumes.
"""
from __future__ import annotations

import copy
import datetime as dt
import re
import unicodedata
from pathlib import Path
from typing import Any

from deck_builder import highlight
from deck_builder import template as tpl
from deck_builder.brand.registry import Brand
from deck_builder.build.visuals import (
    CELL_PAD_EMU,
    CHAR_EM,
    CODE_TITLE_LINES,
    TABLE_DEFAULTS,
    column_widths,
    number_columns,
)
from deck_builder.errors import Issue
from deck_builder.model import Chart, Code, Deck, Icon, Image, Slide, Table, Value, kind_of

STARTER_ICONS = Path(__file__).resolve().parent / "data" / "icons"  # alpha masks every brand can use
CHART_TYPES = ("column", "stacked-column", "bar", "stacked-bar", "line", "pie", "doughnut")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
EMU_PER_PT = 12700
INLINE = [
    (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),
    (re.compile(r"\*\*\*(.+?)\*\*\*"), r"\1"),
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
    if isinstance(value, Code):
        return value.text
    return str(value)


def _asset_id(ref: str) -> str | None:
    """The id in brand:logo/<id> or brand:icon/<id>; None if it could name a path."""
    aid = ref.split("/", 1)[1]
    return None if not aid or "/" in aid or "\\" in aid or ".." in aid else aid


def confined(path: Path, root: Path) -> bool:
    """Whether path resolves inside root, following symlinks - the test every asset read must pass
    before an existence test, hash or image decode, not only when check reports ASSET_OUTSIDE."""
    return path.resolve().is_relative_to(root.resolve())


def resolve_asset_confined(ref: str, brand: Brand, deck_dir: Path) -> tuple[Path | None, str | None]:
    """resolve_asset, plus the confinement check _check_asset applies: a brand: reference must stay
    inside the brand's kit (or the engine's starter icons), anything else inside the deck's folder.
    Callers that only inventory or hash a resolved asset (assets.py, the importer's known-asset scan)
    must go through this, not resolve_asset directly, so a path that escapes is refused before it's
    opened."""
    path, err = resolve_asset(ref, brand, deck_dir)
    if err or path is None:
        return None, err
    roots = [brand.path, STARTER_ICONS] if ref.startswith("brand:icon/") else [
        brand.path if ref.startswith("brand:") else deck_dir]
    if not any(confined(path, root) for root in roots):
        return None, "ASSET_OUTSIDE"
    return path, None


def starter_icons() -> list[str]:
    """The ids of the icons every brand has: the engine's starter set, used when a kit has no icon by
    that id, so a new kit doesn't start with none."""
    return sorted(p.stem for p in STARTER_ICONS.glob("*.png"))


def asset_source(path: Path, ref: str, brand: Brand, deck_dir: Path) -> str:
    """Where a resolved asset came from, for the manifest: relative to the kit or the deck's folder,
    or `starter/<id>.png` for a starter icon."""
    full = path.resolve()
    if ref.startswith("brand:") and full.is_relative_to(brand.path.resolve()):
        return full.relative_to(brand.path.resolve()).as_posix()
    if full.is_relative_to(STARTER_ICONS.resolve()):
        return f"starter/{full.name}"
    return full.relative_to(deck_dir.resolve()).as_posix()


def resolve_asset(ref: str, brand: Brand, deck_dir: Path) -> tuple[Path | None, str | None]:
    """A reference -> (file path, error code or None). An icon the kit lacks comes from the starter set."""
    if ref.startswith("brand:logo/"):
        lid = _asset_id(ref)
        rel = (brand.meta.get("logos") or {}).get(lid) if lid else None
        if not rel:
            return None, "UNKNOWN_ASSET"
        return brand.path / str(rel), None
    if ref.startswith("brand:icon/"):
        iid = _asset_id(ref)
        if not iid:
            return None, "UNKNOWN_ASSET"
        icons_dir = (brand.meta.get("icons") or {}).get("dir")
        for p in ([brand.path / str(icons_dir) / f"{iid}.png"] if icons_dir else []) + [STARTER_ICONS / f"{iid}.png"]:
            if p.is_file():
                return p, None
        return None, "UNKNOWN_ASSET"
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


def _check_front_matter(deck: Deck) -> list[Issue]:
    """Front matter values that would otherwise crash build, parse.markdown or render with no issue code,
    such as `dt.date.fromisoformat` on a non-ISO date. Caught here, check fails loudly before build runs."""
    out: list[Issue] = []
    at: dict[str, Any] = {"file": _file(deck), "line": 1}
    meta = deck.meta
    raw_date = meta.get("date")
    if raw_date is not None and not isinstance(raw_date, dt.date):
        try:
            dt.date.fromisoformat(str(raw_date))
        except ValueError:
            out.append(Issue("PARSE", f"front matter date: {raw_date!r} isn't a date PowerPoint can use; "
                             "write it as YYYY-MM-DD", **at))
    sv = meta.get("spec_version")
    if sv is not None and (isinstance(sv, bool) or not isinstance(sv, int)):
        out.append(Issue("PARSE", f"front matter spec_version: {sv!r} must be a whole number", **at))
    sl = meta.get("slide_level")
    if sl is not None and (isinstance(sl, bool) or not isinstance(sl, int) or not 1 <= sl <= 6):
        out.append(Issue("PARSE", f"front matter slide_level: {sl!r} must be a whole number from 1 to 6", **at))
    first = meta.get("first_slide_number")
    if first is not None and (isinstance(first, bool) or not isinstance(first, int) or first < 1):
        out.append(Issue("PARSE", f"front matter first_slide_number: {first!r} must be a whole number from 1 up",
                         **at))
    kicker = meta.get("kicker")
    if kicker is not None and not isinstance(kicker, str | int | float):
        out.append(Issue("PARSE", f"front matter kicker: {kicker!r} must be one line of text", **at))
    # output: isn't checked here. default_output() already confines and validates it with a clear EnvError
    # at build time; duplicating that here would need the workspace config this function doesn't have.
    return out


def resolve(deck: Deck, brand: Brand, deck_dir: Path) -> tuple[Deck, list[Issue]]:
    deck = copy.deepcopy(deck)
    issues: list[Issue] = _check_front_matter(deck)
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

    kicker = deck.meta.get("kicker")
    for n, s in enumerate(deck.slides, start=1):
        fields_of = (spec_layouts.get(s.layout) or {}).get("fields") or {}
        if isinstance(kicker, str | int | float) and "kicker" in fields_of and "kicker" not in s.fields:
            s.fields["kicker"] = str(kicker)  # the deck-wide section label, where a slide sets none
        issues += _check_slide(s, n, spec_layouts, prs_layouts, brand, deck_dir, banned)
    issues += _conventions(deck, brand, spec_layouts)
    return deck, issues


# Limits from the design research (`docs design`): convention, not standard, so they warn and never fail.
MAX_BULLETS, MAX_WORDS, MAX_RUN, MAX_SERIES, MAX_CODE_LINES, MAX_CONTRASTS = 4, 60, 3, 8, 12, 2

# The countable writing tells on slide text (`docs design`, "Writing on slides"). Each word is wrong on a slide
# in any context; words a brand can use literally ("journey", "landscape") are left to the agents' judgment.
PROSE_WORDS = {
    "inflated word": ("leverage", "leveraging", "leveraged", "utilize", "utilizes", "utilizing", "unlock", "unlocks",
                      "empower", "empowers", "seamless", "seamlessly", "robust", "holistic", "synergy", "synergies",
                      "paradigm", "game-changing", "game changer", "cutting-edge", "best-in-class"),
    "intensifier": ("significantly", "dramatically", "incredibly", "crucially", "vitally", "extremely"),
    "filler transition": ("moreover", "furthermore", "that said", "in conclusion", "let's dive in"),
    "teaser": ("the surprising part", "here's the catch", "here's the kicker", "changes everything"),
}
PROSE_SYMBOLS = {"—": " - ", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "...", "→": "->", "←": "<-"}
PROSE_FIX = {"symbol": "type the plain form", "emoji": "cut it", "inflated word": "say what it does in plain words",
             "intensifier": "give the number, or cut the word", "filler transition": "cut it; the order does that work",
             "teaser": "state the point instead of teasing it",
             "contrast": f"more than {MAX_CONTRASTS} \"X, not Y\" contrasts in the deck; state it plainly"}
_PROSE = {kind: re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in words) + r")(?![\w-])", re.IGNORECASE)
          for kind, words in PROSE_WORDS.items()}
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
CONTRAST = re.compile(r",\s+not\s+\w+", re.IGNORECASE)
QUOTED = re.compile(r'"[^"\n]*"')


def prose_tells(text: str) -> dict[str, list[str]]:
    """The writing tells in slide text, by kind: symbols, emoji, inflated words, intensifiers, filler
    transitions, teasers, and "X, not Y" contrasts. Inline code and quoted words are someone else's and skip."""
    text = QUOTED.sub("", plain(INLINE_CODE.sub("", text)))
    found: dict[str, list[str]] = {}
    symbols = [s for s in PROSE_SYMBOLS if s in text]
    if symbols:
        found["symbol"] = [f"{s} (use {PROSE_SYMBOLS[s].strip() or s})" for s in symbols]
    if emoji := EMOJI.findall(text):
        found["emoji"] = emoji
    for kind, pat in _PROSE.items():
        if hits := [m.group(1) for m in pat.finditer(text)]:
            found[kind] = hits
    if contrasts := CONTRAST.findall(text):
        found["contrast"] = contrasts
    return found


def _conventions(deck: Deck, brand: Brand, spec_layouts: dict[str, Any]) -> list[Issue]:
    """Warnings for slides past the design rules' working limits: more than four bullets in a list or
    60 words on a projected slide, more than three slides in a row on one layout, more than eight series
    in a chart. A read deck (generate.mode: read) holds more text, so the text limits skip it.

    Also the accessibility checks a deck can fail on its own (WCAG 2.2): an image with no alt text
    (1.1.1), two slides with the same title (2.4.6, and PowerPoint's own accessibility checker), and a
    chart whose series or slices are told apart by color alone (1.4.1)."""
    out: list[Issue] = []
    projected = ((brand.meta.get("generate") or {}).get("mode", "projected")) != "read"
    run = contrasts = 0
    titles: dict[str, int] = {}
    for n, s in enumerate(deck.slides, start=1):
        at: dict[str, Any] = {"file": s.where.file if s.where else None,
                              "line": s.where.line if s.where else None, "slide": n}
        key = " ".join(plain(s.title).lower().split())
        if key and key in titles:
            out.append(Issue("TITLE_DUPLICATE", f"the same title as slide {titles[key]}: {s.title!r}; a screen "
                             "reader lists slides by title, so make each one say what its slide shows",
                             severity="warning", **at))
        titles.setdefault(key, n)
        for name, val in s.fields.items():
            if isinstance(val, Image) and not val.alt.strip():
                out.append(Issue("MISSING_ALT", f"{val.ref!r} has no alt text; write what it shows in "
                                 "![alt](path)", field=name, severity="warning", **at))
            if isinstance(val, Chart) and val.legend is False and not val.labels and \
                    (len(val.series) > 1 or val.type in ("pie", "doughnut")):
                out.append(Issue("COLOR_ONLY", "this chart's series are told apart by color alone; turn on "
                                 "legend: or labels:", field=name, severity="warning", **at))
        prev = deck.slides[n - 2].layout if n > 1 else None
        run = run + 1 if s.layout and s.layout == prev else 1
        if run == MAX_RUN + 1:
            out.append(Issue("LAYOUT_RUN", f"slides {n - MAX_RUN} to {n} all use {s.layout!r}; vary the layout "
                             "with the content", severity="warning", **at))
        fields_of = (spec_layouts.get(s.layout) or {}).get("fields") or {}
        words = 0
        for name, val in s.fields.items():
            if isinstance(val, Chart) and len(val.series) > MAX_SERIES:
                out.append(Issue("SERIES_MANY", f"{len(val.series)} series; eight is the most a chart's colors keep "
                                 "apart", field=name, severity="warning", actual=len(val.series), limit=MAX_SERIES,
                                 **at))
            if projected and isinstance(val, Code) and len(val.lines) > MAX_CODE_LINES:
                out.append(Issue("CODE_LINES_MANY", f"{len(val.lines)} lines of code on a projected slide; "
                                 f"{MAX_CODE_LINES} or fewer read in the time a slide is up", field=name,
                                 severity="warning", actual=len(val.lines), limit=MAX_CODE_LINES, **at))
            if isinstance(val, Table | Chart | Image | Icon | Code):
                continue
            if name != "quote":  # a quote is someone else's words
                tells = prose_tells(text_of(val))
                for kind, found in tells.items():
                    if kind == "contrast":
                        contrasts += len(found)
                        if contrasts <= MAX_CONTRASTS:
                            continue
                    out.append(Issue("PROSE_TELL", f"{kind} {', '.join(repr(f) for f in found)}: {PROSE_FIX[kind]}",
                                     field=name, severity="warning", **at))
            words += len(plain(text_of(val)).split())
            if projected and isinstance(val, list) and len(val) > MAX_BULLETS and \
                    (fields_of.get(name) or {}).get("kind") == "bullets":
                out.append(Issue("BULLETS_MANY", f"{len(val)} bullets on a projected slide; four or fewer read "
                                 "best", field=name, severity="warning", actual=len(val), limit=MAX_BULLETS, **at))
        if projected and words > MAX_WORDS:
            out.append(Issue("WORDS_MANY", f"{words} words on a projected slide; move detail to the notes",
                             severity="warning", actual=words, limit=MAX_WORDS, **at))
    return out


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
    layout = tpl.find_layout(prs_layouts, str(tl), ls.get("master")) if prs_layouts else None
    if prs_layouts and layout is None:
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
            if s.build == "body":
                s.build = cands[0]
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
        out += _check_field(name, s.fields[name], fs, want, brand, deck_dir, layout, at)
        fv = s.fields[name]
        txt = text_of(fv) if isinstance(fv, Code) else plain(text_of(fv))  # code has no inline markup
        for pat in banned:
            if pat.search(txt):
                out.append(Issue("BANNED_PATTERN", f"matches {pat.pattern!r}", field=name, **at))
    for pat in banned:
        if s.notes and pat.search(s.notes):
            out.append(Issue("BANNED_PATTERN", f"speaker notes match {pat.pattern!r}", field="notes", **at))
    for name, fs in fspecs.items():
        val = s.fields.get(name)
        if fs.get("required") and (val is None or (isinstance(val, str) and not val.strip())):
            out.append(Issue("MISSING_FIELD", f"required field {name!r} is empty", field=name, **at))
    if s.current is not None:
        out += _check_current(s, fspecs, at)
    if s.build is not None:
        out += _check_build(s, fspecs, at)
    return out


SLOT_FIELD = re.compile(r"\D+(\d+)$")  # label2, body2 and footer2 are slot 2 of a cards layout


def _check_build(s: Slide, fspecs: dict[str, Any], at: dict[str, Any]) -> list[Issue]:
    """`build:` names `slots` on a layout with numbered slots, or a field this slide fills that isn't code."""
    b = s.build
    if b == "slots":
        slots = {m.group(1) for k in s.fields if k in fspecs and (m := SLOT_FIELD.match(k))}
        if len(slots) > 1:
            return []
        return [Issue("PARSE", f"build: slots needs two or more filled slots (cards, steps, bands); layout "
                      f"{s.layout!r} has {len(slots)}", field="build", **at)]
    if not isinstance(b, str) or b not in s.fields or b not in fspecs:
        return [Issue("PARSE", f"build: {b!r} must be `slots` or a field this slide fills "
                      f"({', '.join(k for k in s.fields if k in fspecs)})", field="build", **at)]
    if isinstance(s.fields[b], Code):
        return [Issue("PARSE", "build: a code block doesn't build; mark the lines with {3,5-7} instead",
                      field="build", **at)]
    return []


CARD_LABEL = re.compile(r"^label(\d+)$")


def current_slots(s: Slide, fspecs: dict[str, Any]) -> int:
    """How many things `current:` can mark on this slide: its cards on a cards layout, else the items of its
    `body` list (an agenda, or any list), else 0."""
    if s.layout.startswith("cards-"):
        return sum(1 for k in fspecs if CARD_LABEL.match(k))
    body = s.fields.get("body")
    return len(body) if isinstance(body, list) and (fspecs.get("body") or {}).get("kind") == "bullets" else 0


def _check_current(s: Slide, fspecs: dict[str, Any], at: dict[str, Any]) -> list[Issue]:
    count, n = current_slots(s, fspecs), s.current
    if not count:
        return [Issue("PARSE", f"current: marks a card or a list item, and layout {s.layout!r} has neither "
                      "cards nor a body list", field="current", **at)]
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= count:
        return [Issue("PARSE", f"current: {n!r} must be a whole number from 1 to {count}", field="current", **at)]
    return []


def _check_field(name: str, val: Value, fs: dict[str, Any], want: str, brand: Brand, deck_dir: Path,
                 layout: Any, at: dict[str, Any]) -> list[Issue]:
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
    if want in ("text", "bullets") and fs.get("line_chars") and fs.get("max_lines"):
        out += _check_lines(name, val, fs, want, at)
    if want in ("text", "bullets") and fs.get("line_chars"):
        out += _check_spans(name, val, int(fs["line_chars"]), at)
    if isinstance(val, Code):
        out += _check_code(name, val, fs, at)
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
        out += _check_table(name, val, fs, brand, layout, at)
    if isinstance(val, Chart):
        out += _check_chart(name, val, brand, at)
    if isinstance(val, Image | Icon):
        out += _check_asset(name, val.ref, brand, deck_dir, at)
    return out


BULLET_GAP_LINES = 0.5 / 1.2  # the space before each bullet, half its size, as a share of a line


def _wrapped(text: str, per_line: int) -> int:
    """Lines a paragraph wraps to at per_line characters, word by word; a word longer than a line breaks."""
    lines, used = 1, 0
    for word in text.split():
        need = len(word) if used == 0 else used + 1 + len(word)
        if need <= per_line:
            used = need
            continue
        if used:  # the word starts a new line
            lines += 1
        while len(word) > per_line:  # a word longer than a line breaks across lines
            lines += 1
            word = word[per_line:]
        used = len(word)
    return lines


def _check_lines(name: str, val: Value, fs: dict[str, Any], want: str, at: dict[str, Any]) -> list[Issue]:
    """BUDGET_LINES when the text, wrapped at the field's line length, needs more lines than its box
    holds: a list counts each bullet's own lines and the space before it, which a character count
    can't see when short lines make every bullet wrap."""
    items = [t for _, t in val] if isinstance(val, list) else [str(val)]
    lines = sum(_wrapped(plain(t), int(fs["line_chars"])) for t in items)
    need = lines + (len(items) * BULLET_GAP_LINES if want == "bullets" else 0.0)
    if need > fs["max_lines"] + 1e-9:
        return [Issue("BUDGET_LINES", f"wraps to about {need:.1f} lines at {fs['line_chars']} characters a line; "
                      f"the box holds {fs['max_lines']:g}", field=name, actual=round(need, 1),
                      limit=fs["max_lines"], **at)]
    return []


INLINE_CODE = re.compile(r"`([^`]+)`")


def _check_spans(name: str, val: Value, per_line: int, at: dict[str, Any]) -> list[Issue]:
    """CODE_LONG as a warning for an inline `code` span longer than a line of its field: a token such as
    `warehouse.orders.shipped_at` has no space to wrap at, so the renderer breaks it mid-token."""
    items = [t for _, t in val] if isinstance(val, list) else [str(val)]
    return [Issue("CODE_LONG", f"inline code {span[:40]!r} is {len(span)} characters, and a line of this field "
                  f"holds about {per_line}; it will break mid-token", field=name, severity="warning",
                  actual=len(span), limit=per_line, **at)
            for t in items for span in INLINE_CODE.findall(t) if len(span) > per_line]


def code_width(line: str) -> int:
    """Columns a line of code takes in a monospace font: East Asian wide characters take two."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in line)


def _check_code(name: str, c: Code, fs: dict[str, Any], at: dict[str, Any]) -> list[Issue]:
    """Code never wraps: CODE_LONG for each line past the panel's width and for more lines than it holds,
    and CODE_LANGUAGE (a warning) when the language has no highlighter, so it builds as plain text."""
    out: list[Issue] = []
    if not highlight.known(c.language):
        out.append(Issue("CODE_LANGUAGE", f"{c.language!r} isn't a language the highlighter knows; the block "
                         "builds as plain text", field=name, severity="warning", **at))
    cols = int(fs["max_cols"]) - number_columns(c) if fs.get("max_cols") else None
    numbers = " beside its line numbers" if c.numbers else ""
    for k, ln in enumerate(c.lines, start=1):
        if cols and (w := code_width(ln)) > cols:
            out.append(Issue("CODE_LONG", f"line {k} is {w} characters, and the panel holds {cols}{numbers}: "
                             f"{ln.strip()[:40]!r}", field=name, actual=w, limit=cols, **at))
    if fs.get("max_lines"):
        room = int(fs["max_lines"]) - (CODE_TITLE_LINES if c.title else 0)
        if len(c.lines) > room:
            with_title = f" (the filename line takes {CODE_TITLE_LINES})" if c.title else ""
            out.append(Issue("CODE_LONG", f"{len(c.lines)} lines, and the panel holds {room}{with_title}",
                             field=name, actual=len(c.lines), limit=room, **at))
    return out


def _check_table(name: str, t: Table, fs: dict[str, Any], brand: Brand, layout: Any,
                 at: dict[str, Any]) -> list[Issue]:
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
    out += _check_table_height(name, t, fs, brand, layout, at)
    return out


def _wrapped_lines(text: str, col_width_pt: float, font_size_pt: float) -> int:
    """A rough estimate of how many lines a cell's text wraps to at a column width, word by word: no
    real font metrics at check time, so an average glyph is taken as CHAR_EM of the font size wide."""
    if not text or col_width_pt <= 0:
        return 1
    per_line = max(1, int(col_width_pt / (font_size_pt * CHAR_EM)))
    lines, used = 1, 0
    for word in text.split():
        need = len(word) if used == 0 else used + 1 + len(word)
        if need <= per_line or used == 0:
            used = need
        else:
            lines, used = lines + 1, len(word)
    return lines


def _check_table_height(name: str, t: Table, fs: dict[str, Any], brand: Brand, layout: Any,
                        at: dict[str, Any]) -> list[Issue]:
    idx = fs.get("idx")
    if idx is None or layout is None:
        return []
    ph = next((p for p in layout.placeholders if p.placeholder_format.idx == idx), None)
    if ph is None or ph.width is None or ph.height is None:
        return []
    height_pt = ph.height / EMU_PER_PT
    tok = {**TABLE_DEFAULTS, **(brand.tokens.get("table") or {})}
    font_size = max(tok["font_size"], tok["header_font_size"])
    row_h = font_size * tok["row_height_factor"]
    if not t.header or any(len(r) != len(t.header) for r in t.rows):
        return []
    # the same column widths build gives the table, less each cell's insets
    widths = [(w - CELL_PAD_EMU) / EMU_PER_PT for w in column_widths(t, int(ph.width), font_size)]
    est_height = 0.0
    for row in [t.header, *t.rows]:
        lines = max(_wrapped_lines(plain(c), w, font_size) for c, w in zip(row, widths, strict=True))
        est_height += max(row_h, lines * font_size * 1.2 + 7.2)  # a wrapped row grows past its set height
    if est_height > height_pt:
        return [Issue("TABLE_TALL",
                      f"estimated table height {est_height:.0f} pt exceeds its placeholder's {height_pt:.0f} pt",
                      severity="warning", field=name, actual=round(est_height), limit=round(height_pt), **at)]
    return []


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
    if ref.startswith("!["):  # a quoted `field: "![alt](path)"` line
        return [Issue("ASSET_FORMAT", f"{ref!r} is image markdown on a field line; put the ![alt](path) line "
                      f"in a `### {name}` section instead", field=name, **at)]
    if re.match(r"^[a-z][a-z0-9+.-]*://", ref, re.IGNORECASE):
        return [Issue("MISSING_IMAGE", f"{ref!r} is a web address; images must be local files, so download it "
                      "into the deck folder and use its path", field=name, **at)]
    path, err = resolve_asset_confined(ref, brand, deck_dir)
    if err == "ASSET_OUTSIDE":
        where = f"brand {brand.slug!r}'s kit" if ref.startswith("brand:") else "the deck's folder"
        return [Issue("ASSET_OUTSIDE", f"{ref!r} is outside {where}; copy the image into it and use that path",
                      field=name, **at)]
    if err:
        return [Issue(err, f"{ref!r} isn't defined in brand {brand.slug!r}", field=name, **at)]
    assert path is not None
    if path.suffix.lower() == ".svg":
        return [Issue("ASSET_FORMAT", f"{ref!r} is SVG; convert it to PNG", field=name, **at)]
    if path.suffix.lower() not in IMAGE_EXT:
        return [Issue("ASSET_FORMAT", f"{ref!r}: unsupported image type {path.suffix}", field=name, **at)]
    if not path.is_file():
        return [Issue("MISSING_IMAGE", f"{ref!r} not found; paths resolve relative to the deck file",
                      field=name, **at)]
    return []
