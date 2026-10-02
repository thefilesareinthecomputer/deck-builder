"""Measured overflow: where the renderer actually put each word, against the box it belongs in.

`pdftotext -bbox-layout` gives every word's box on the rendered page. Each word is assigned to the
nearest text shape whose text contains it, and any assigned word outside its shape's box beyond a
small tolerance is overflow. Exact on PowerPoint's PDF; a close proxy on LibreOffice's. The
assignment is a heuristic: a word shared by two adjacent shapes goes to the nearer one.
"""
from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pptx import Presentation

from deck_builder.errors import Issue

EMU_PER_PT = 12700
TOLERANCE_PT = 3.0
VERTICAL_SLACK = 0.15  # of a word box's height; see overshoot()
TOKEN = re.compile(r"[\w%$€£.,:'-]+", re.UNICODE)


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


def norm(token: str) -> str:
    return token.strip(".,:;'\"").lower()


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


def text_shapes(pptx: Path) -> tuple[float, list[tuple[list[TextShape], list[Box]]]]:
    """Slide width in points, and per slide: the shapes holding text, and the boxes of charts and tables,
    whose own words are left out of the measurement."""
    prs = Presentation(str(pptx))
    out = []
    for slide in prs.slides:
        shapes, visuals = [], []
        for sh in slide.shapes:
            if sh.left is None or sh.width is None:
                continue
            if getattr(sh, "has_chart", False) or getattr(sh, "has_table", False):
                visuals.append(_box(sh))
                continue
            if not getattr(sh, "has_text_frame", False) or not sh.text_frame.text.strip():
                continue
            tokens = {norm(t) for t in TOKEN.findall(sh.text_frame.text)} - {""}
            shapes.append(TextShape(sh.name, _box(sh), tokens))
        out.append((shapes, visuals))
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


def overflow(pptx: Path, pdf: Path, manifest: dict[str, Any] | None = None,
            visible: list[int] | None = None) -> list[Issue]:
    """`visible` maps PDF page order to real slide numbers (see images.rasterize); default is 1..N, every
    slide visible."""
    slide_w, slides = text_shapes(pptx)
    if visible is None:
        visible = list(range(1, len(slides) + 1))
    issues = []
    for n, (page_w, _, words) in zip(visible, pdf_words(pdf), strict=False):
        shapes, visuals = slides[n - 1]
        scale = page_w / slide_w if slide_w else 1.0
        assigned: dict[int, list[Word]] = {}
        for w in words:
            t = norm(w.text)
            x, y = (c / scale for c in w.center)
            if any(v.distance(x, y) == 0 for v in visuals):
                continue  # a chart's or table's own text
            cands = [(s.box.distance(x, y), i) for i, s in enumerate(shapes) if t in s.tokens]
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
