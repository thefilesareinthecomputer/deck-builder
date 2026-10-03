"""Measured overflow: where the renderer actually put each word, against the box it belongs in.

`pdftotext -bbox-layout` gives every word's box on the rendered page. Each word is assigned to the
nearest text shape whose text contains it, and any assigned word outside its shape's box beyond a
small tolerance is overflow. Exact on PowerPoint's PDF; a close proxy on LibreOffice's. The
assignment is a heuristic: a word shared by two adjacent shapes goes to the nearer one, preferring
one whose box contains the word outright.

Tables are measured too, against their layout placeholder's box rather than their own nominal frame
(row height times row count), which the renderer ignores once wrapped cells grow past it. The footer
and slide-number placeholders only ever take a word that actually sits inside their own small box, so
a table's wrapped words never get mistaken for footer overflow, and a list's auto-numbered marker
("1.", "2.", a bullet glyph) never gets mistaken for a page number.

A word that matches no shape's token at all is left unassigned rather than discarded for sitting over
a chart or table, so a shape's own overflowing word is still measured even where it visually spills
onto a neighboring visual. A renderer that wraps a long, spaceless word mid-word leaves neither
fragment equal to the source token; each fragment is matched to the shape whose token contains it.
"""
from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.oxml.ns import qn

from deck_builder.build.visuals import CODE_DESCR
from deck_builder.errors import Issue

EMU_PER_PT = 12700
TOLERANCE_PT = 3.0
VERTICAL_SLACK = 0.15  # of a word box's height; see overshoot()
TOKEN = re.compile(r"[\w%$€£.,:'-]+", re.UNICODE)
LIST_MARKER = re.compile(r"^\d+[.)]$")  # an auto-numbered list's own marker, e.g. "1." or "2)"
CHART_NUMBER = re.compile(r"^[+\-−]?[$€£]?[\d.,]+%?$")  # an axis tick or data label inside a chart
BULLET_GLYPHS = {"•", "◦", "‣", "∙", "●", "○", "■", "▪", "▸", "–", "—", "*", "·"}
PROTECTED_TYPES = {PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.SLIDE_NUMBER}
MIN_FRAGMENT = 3  # a shorter rendered fragment is too ambiguous to trust as a split token


@dataclass
class Box:
    left: float
    top: float
    right: float
    bottom: float

    def distance(self, x: float, y: float) -> float:
        dx = max(self.left - x, 0.0, x - self.right)
        dy = max(self.top - y, 0.0, y - self.bottom)
        return (dx * dx + dy * dy) ** 0.5


@dataclass
class Word:
    text: str
    box: Box

    @property
    def center(self) -> tuple[float, float]:
        return (self.box.left + self.box.right) / 2, (self.box.top + self.box.bottom) / 2


@dataclass
class TextShape:
    name: str
    box: Box
    tokens: set[str]
    protected: bool = False  # the footer or slide-number placeholder: only a word truly inside it counts
    chart: bool = False  # a chart's area: never takes words, but keeps its own text from other shapes


def norm(token: str) -> str:
    return token.strip(".,:;'\"").lower()


def is_list_marker(text: str) -> bool:
    """A bare auto-numbered list marker or bullet glyph, pdftotext's own word for it: never in any
    shape's text, so it must never be matched to one by token."""
    return text in BULLET_GLYPHS or bool(LIST_MARKER.match(text))


def pdf_words(pdf: Path) -> list[tuple[float, float, list[Word]]]:
    """Per page: (width, height, words), in points from the top-left."""
    out = subprocess.run(["pdftotext", "-bbox-layout", str(pdf.resolve()), "-"], capture_output=True, text=True,
                         check=True, timeout=120).stdout
    root = ET.fromstring(re.sub(r"<!DOCTYPE[^>]*>", "", out))
    pages = []
    for page in root.iter():
        if not page.tag.endswith("page"):
            continue
        words = []
        for w in page.iter():
            if w.tag.endswith("word") and w.text:
                b = Box(float(w.get("xMin", 0)), float(w.get("yMin", 0)), float(w.get("xMax", 0)),
                        float(w.get("yMax", 0)))
                words.append(Word(w.text, b))
        pages.append((float(page.get("width", 0)), float(page.get("height", 0)), words))
    return pages


def _box(sh: Any) -> Box:
    return Box(sh.left / EMU_PER_PT, sh.top / EMU_PER_PT, (sh.left + sh.width) / EMU_PER_PT,
               (sh.top + sh.height) / EMU_PER_PT)


def _layout_placeholder_box(sh: Any, layout: Any) -> Box:
    """A placeholder shape's box on its slide layout, not its own (the layout's is the brand's intended
    area; a table's own box is row height times row count, which the renderer ignores once wrapped
    cells grow past it). Falls back to the shape's own box when the layout has no matching idx."""
    if layout is not None and getattr(sh, "is_placeholder", False):
        idx = sh.placeholder_format.idx
        for ph in layout.placeholders:
            if ph.placeholder_format.idx == idx and ph.left is not None and ph.width is not None:
                return _box(ph)
    return _box(sh)


def _table_tokens(sh: Any) -> set[str]:
    tokens: set[str] = set()
    for row in sh.table.rows:
        for cell in row.cells:
            tokens |= {norm(t) for t in TOKEN.findall(cell.text_frame.text)}
    return tokens - {""}


def _chart_tokens(sh: Any) -> set[str]:
    """The words a chart draws itself: its title, series names and categories."""
    chart = sh.chart
    text = " ".join(str(s.name or "") for plot in chart.plots for s in plot.series)
    text += " " + " ".join(str(c) for plot in chart.plots for c in plot.categories)
    if chart.has_title:
        text += " " + chart.chart_title.text_frame.text
    return {norm(t) for t in TOKEN.findall(text)} - {""}


def _is_code(sh: Any) -> bool:
    """A code block the build made: its alt text names the language (`python code`)."""
    cnvpr = sh._element.find(f"{qn('p:nvSpPr')}/{qn('p:cNvPr')}")
    return cnvpr is not None and bool(CODE_DESCR.match(str(cnvpr.get("descr") or "")))


def _is_protected(sh: Any) -> bool:
    return bool(getattr(sh, "is_placeholder", False)) and sh.placeholder_format.type in PROTECTED_TYPES


def text_shapes(pptx: Path) -> tuple[float, list[list[TextShape]]]:
    """Slide width in points, and per slide the shapes measured for overflow (text frames and
    tables). A chart's own rendered text (axis labels, data labels) isn't tracked as a shape, so a
    word that matches none of a slide's shapes is simply left unassigned, whether or not it sits over
    a chart; a word that does match a shape is assigned to it regardless of what it visually overlaps."""
    prs = Presentation(str(pptx))
    out = []
    for slide in prs.slides:
        layout = slide.slide_layout
        shapes: list[TextShape] = []
        for sh in slide.shapes:
            if sh.left is None or sh.width is None:
                continue
            if getattr(sh, "has_chart", False):
                shapes.append(TextShape(sh.name, _box(sh), _chart_tokens(sh), chart=True))
                continue
            if getattr(sh, "has_table", False):
                shapes.append(TextShape(sh.name, _layout_placeholder_box(sh, layout), _table_tokens(sh)))
                continue
            if not getattr(sh, "has_text_frame", False) or not sh.text_frame.text.strip():
                continue
            tokens = {norm(t) for t in TOKEN.findall(sh.text_frame.text)} - {""}
            if _is_code(sh):  # code splits only at spaces, as pdftotext does: `df.groupby("week")` is one word
                tokens |= {norm(t) for t in sh.text_frame.text.split()} - {""}
            shapes.append(TextShape(sh.name, _box(sh), tokens, protected=_is_protected(sh)))
        out.append(shapes)
    return prs.slide_width / EMU_PER_PT, out


def overshoot(box: Box, words: list[Box]) -> float:
    """How far a shape's words run past its box, in points, or 0 when they fit.

    A word's box spans the font's full ascent and descent, which runs past the ink by up to about 15%
    of the line in tall-metric fonts (Avenir Next), so the vertical edges allow that much. Text that
    really overflows spills at least one more line, well past it.
    """
    line = max(w.bottom - w.top for w in words)
    vertical = max(max(w.bottom for w in words) - box.bottom, box.top - min(w.top for w in words))
    horizontal = max(max(w.right for w in words) - box.right, box.left - min(w.left for w in words))
    over = [horizontal] if horizontal > TOLERANCE_PT else []
    if vertical > max(TOLERANCE_PT, VERTICAL_SLACK * line):
        over.append(vertical)
    return max(over, default=0.0)


def _fragment_of(t: str, tokens: set[str]) -> bool:
    """t is a piece of a longer source token: a renderer that wraps a long word mid-word (no space to
    break on) produces fragments that are each a plain substring of it, none equal to the whole thing."""
    return len(t) >= MIN_FRAGMENT and any(tok != t and t in tok for tok in tokens)


def _candidates(t: str, x: float, y: float, shapes: list[TextShape]) -> list[tuple[float, int]]:
    """The shapes a word could belong to, nearest first (0 when its point is inside the box). A word
    inside a shape that holds it, exactly or as a fragment of a word the renderer split, belongs to that
    shape; otherwise exact token matches win over split-fragment matches. The footer and slide number
    only ever take a word that's actually inside their own small box, so neither steals overflow from a
    nearby shape."""
    def near(pool: list[int]) -> list[tuple[float, int]]:
        out = []
        for i in pool:
            s = shapes[i]
            d = s.box.distance(x, y)
            if not (s.protected and d != 0):
                out.append((d, i))
        return out

    exact = near([i for i, s in enumerate(shapes) if not s.chart and t in s.tokens])
    split = near([i for i, s in enumerate(shapes) if not s.chart and t not in s.tokens and _fragment_of(t, s.tokens)])
    inside = [c for c in exact + split if c[0] == 0]  # "tested" inside the chevron that holds "load-tested"
    return inside or exact or split


def overflow(pptx: Path, pdf: Path, manifest: dict[str, Any] | None = None,
            visible: list[int] | None = None) -> list[Issue]:
    """`visible` maps PDF page order to real slide numbers (see images.rasterize); default is 1..N, every
    slide visible."""
    slide_w, slides = text_shapes(pptx)
    if visible is None:
        visible = list(range(1, len(slides) + 1))
    issues = []
    for n, (page_w, _, words) in zip(visible, pdf_words(pdf), strict=False):
        shapes = slides[n - 1]
        scale = page_w / slide_w if slide_w else 1.0
        assigned: dict[int, list[Word]] = {}
        for w in words:
            if is_list_marker(w.text):
                continue  # a list's own auto-numbered marker or bullet: not in any shape's text
            t = norm(w.text)
            x, y = (c / scale for c in w.center)
            if any(s.chart and s.box.distance(x, y) == 0 and (t in s.tokens or CHART_NUMBER.match(t))
                   for s in shapes):
                continue  # the chart's own legend, category, title or axis text, not another shape's overflow
            cands = _candidates(t, x, y, shapes)
            if cands:
                assigned.setdefault(min(cands)[1], []).append(w)
        for i, ws in assigned.items():
            s = shapes[i]
            over = overshoot(s.box, [Box(w.box.left / scale, w.box.top / scale, w.box.right / scale,
                                         w.box.bottom / scale) for w in ws])
            if over:
                field = _field_for(manifest, n, s.name)
                issues.append(Issue("OVERFLOW_MEASURED", f"text runs {over:.0f} pt past its box ({s.name})",
                                    slide=n, field=field, actual=round(over, 1), limit=TOLERANCE_PT))
    return issues


def _field_for(manifest: dict[str, Any] | None, slide: int, shape_name: str) -> str | None:
    """The build records each text field's shape name in the manifest."""
    if not manifest:
        return None
    try:
        fields = manifest["slides"][slide - 1]["fields"]
    except (KeyError, IndexError):
        return None
    hits = [f for f, v in fields.items() if v.get("shape") == shape_name]
    return hits[0] if len(hits) == 1 else None
