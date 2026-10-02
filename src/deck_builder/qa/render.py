"""Render a built deck: PDF, slide PNGs, contact sheets, measured overflow, font check, flagged slides."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER

from deck_builder.brand.registry import Brand
from deck_builder.build.deck import manifest_path
from deck_builder.errors import Issue
from deck_builder.qa import backends, fonts, images, measure

FLAG_CODES = {"OVERFLOW_MEASURED", "EMPTY_PLACEHOLDER", "ASSET_LOW_RES"}
VISUAL = {PP_PLACEHOLDER.PICTURE, PP_PLACEHOLDER.CHART, PP_PLACEHOLDER.TABLE}


@dataclass
class Rendered:
    backend: str
    out_dir: Path
    pdf: Path
    slides: list[Path]
    contact_sheets: list[Path]
    issues: list[Issue] = field(default_factory=list)

    @property
    def flagged(self) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {}
        for i in self.issues:
            if i.code in FLAG_CODES and i.slide is not None:
                out.setdefault(i.slide, []).append(i.code)
        return dict(sorted(out.items()))


def empty_placeholders(pptx: Path) -> list[Issue]:
    issues = []
    for n, slide in enumerate(Presentation(str(pptx)).slides, start=1):
        for ph in slide.placeholders:
            unfilled_visual = ph._element.tag.endswith("}sp")  # filled ones become p:pic or p:graphicFrame
            if ph.placeholder_format.type in VISUAL:
                if unfilled_visual:
                    issues.append(Issue("EMPTY_PLACEHOLDER", f"an unfilled {ph.name!r} is on the slide", slide=n))
            elif ph.has_text_frame and not ph.text_frame.text.strip():
                issues.append(Issue("EMPTY_PLACEHOLDER", f"{ph.name!r} has no text", slide=n))
    return issues


def render(pptx: Path, backend: str, dpi: int, batch: int, pages: list[int] | None,
           brand: Brand | None) -> Rendered:
    out_dir = pptx.with_name(pptx.stem + ".render")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    pdf = out_dir / "deck.pdf"
    backends.to_pdf(backend, pptx, pdf)
    prs = Presentation(str(pptx))
    total = len(prs.slides)
    w_emu, h_emu = int(prs.slide_width or 0), int(prs.slide_height or 0)
    size = (round(w_emu / 914400 * dpi), round(h_emu / 914400 * dpi))  # 13.33 in x 96 dpi = 1280 px
    pngs = images.rasterize(pdf, out_dir, size, pages, total)
    issues: list[Issue] = []
    if backend == "powerpoint":
        issues.append(Issue("RENDER_UNVERIFIED", "the PowerPoint backend hasn't been verified on a real Mac yet",
                            severity="warning"))
    mpath = manifest_path(pptx)
    manifest: dict[str, Any] | None = json.loads(mpath.read_text()) if mpath.is_file() else None
    issues += measure.overflow(pptx, pdf, manifest)
    issues += empty_placeholders(pptx)
    if brand is not None:
        issues += fonts.check(pdf, brand.meta)
    if pages:
        issues = [i for i in issues if i.slide is None or i.slide in pages]
    result = Rendered(backend, out_dir, pdf, pngs, [], issues)
    result.contact_sheets = images.contact_sheets(pngs, out_dir, batch, set(result.flagged))
    return result
