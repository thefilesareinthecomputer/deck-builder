"""Build a resolved deck into a PPTX and its manifest."""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from PIL import Image as PILImage

from deck_builder import __version__
from deck_builder import template as tpl
from deck_builder.assets import recolor_icon, sha256_file
from deck_builder.brand.registry import Brand
from deck_builder.build.normalize import content_digest, normalize
from deck_builder.build.text import CODE_FONT_DEFAULT, fill_text
from deck_builder.build.visuals import fill_chart, fill_picture, fill_table
from deck_builder.errors import Issue
from deck_builder.model import Chart, Deck, Icon, Image, Slide, Table
from deck_builder.validate import plain, resolve_asset, text_of

EMU_PER_INCH = 914400
MIN_DPI = 150
DEFAULT_DATE = dt.date(2000, 1, 1)


def deck_date(meta: dict[str, Any]) -> dt.datetime:
    raw = meta.get("date", DEFAULT_DATE)
    if isinstance(raw, dt.datetime):
        d = raw.date()
    elif isinstance(raw, dt.date):
        d = raw
    else:
        d = dt.date.fromisoformat(str(raw))
    return dt.datetime(d.year, d.month, d.day, tzinfo=dt.UTC)


def _dpi(path: Path, geo: tuple[int, int, int, int], crop: bool) -> float:
    with PILImage.open(path) as im:
        iw, ih = im.size
    _, _, w, h = geo
    scale = max(w / iw, h / ih) if crop else min(w / iw, h / ih)  # EMU per source pixel
    return EMU_PER_INCH / scale if scale else float("inf")


class Builder:
    def __init__(self, brand: Brand, deck_dir: Path, cache_dir: Path) -> None:
        self.brand = brand
        self.deck_dir = deck_dir
        self.cache_dir = cache_dir
        self.code_font = (brand.tokens.get("text") or {}).get("code_font", CODE_FONT_DEFAULT)
        self.issues: list[Issue] = []

    def _picture(self, slide: Any, ph: Any, ref: str, alt: str, at: dict[str, Any],
                 fentry: dict[str, Any], color: str | None) -> None:
        path, _ = resolve_asset(ref, self.brand, self.deck_dir)
        assert path is not None  # validation guarantees it resolves
        brand_asset = ref.startswith("brand:")
        if color:
            path = recolor_icon(path, color, self.cache_dir)
        geo = fill_picture(slide, ph, path, alt, crop=not brand_asset)
        fentry["asset"] = {"ref": ref, "sha256": sha256_file(path)}
        if _dpi(path, geo, crop=not brand_asset) < MIN_DPI:
            self.issues.append(Issue("ASSET_LOW_RES", f"{ref!r} shows below {MIN_DPI} DPI at this size",
                                     severity="warning", **at))

    def slide(self, prs: Any, layouts: dict[Any, Any], s: Slide, n: int) -> dict[str, Any]:
        ls = self.brand.tokens["layouts"][s.layout]
        tl = ls["template_layout"]
        slide = prs.slides.add_slide(tpl.find_layout(layouts, tl, ls.get("master")))
        phs = {ph.placeholder_format.idx: ph for ph in slide.placeholders}
        entry: dict[str, Any] = {"slide": n, "layout": s.layout, "template_layout": tl, "title": s.title,
                                 "fields": {}}
        used: set[int] = set()
        for name, val in s.fields.items():
            fs = ls["fields"][name]
            idx, kind = fs["idx"], fs.get("kind", "text")
            at: dict[str, Any] = {"slide": n, "field": name, "file": s.where.file if s.where else None}
            ph = phs.get(idx)
            if ph is None:
                self.issues.append(Issue("TEMPLATE_MISMATCH", f"placeholder idx {idx} isn't on layout {tl!r}", **at))
                continue
            used.add(idx)
            fentry: dict[str, Any] = {"idx": idx, "kind": kind}
            if isinstance(val, Chart):
                fill_chart(slide, ph, val, self.brand)
            elif isinstance(val, Table):
                fill_table(slide, ph, val, self.brand)
            elif isinstance(val, Image):
                self._picture(slide, ph, val.ref, val.alt, at, fentry, None)
            elif isinstance(val, Icon):
                icons = self.brand.meta.get("icons") or {}
                color = self.brand.color(fs.get("color") or icons.get("default_color"))
                self._picture(slide, ph, val.ref, "", at, fentry, color)
            else:
                fill_text(ph, val, self.code_font)
                fentry["chars"] = len(plain(text_of(val)))
            entry["fields"][name] = fentry
        for idx, ph in phs.items():
            if idx not in used:  # no empty "Click to add text" boxes left behind
                ph._element.getparent().remove(ph._element)
        if s.notes:
            slide.notes_slide.notes_text_frame.text = s.notes
            entry["notes_chars"] = len(s.notes)
        return entry


def build(deck: Deck, brand: Brand, deck_path: Path, out_path: Path, cache_dir: Path,
          keep_template_slides: bool = False) -> tuple[dict[str, Any], list[Issue]]:
    assert brand.template is not None
    prs = tpl.open_template(brand.template)
    if not keep_template_slides:
        tpl.remove_all_slides(prs)
    layouts = tpl.layouts(prs)
    b = Builder(brand, deck_path.parent, cache_dir)
    slides = [b.slide(prs, layouts, s, n) for n, s in enumerate(deck.slides, start=1)]

    when = deck_date(deck.meta)
    author = str(deck.meta.get("author", ""))
    cp = prs.core_properties
    cp.title = str(deck.meta.get("title", ""))
    cp.author = author
    cp.last_modified_by = author
    cp.comments = ""
    cp.revision = 1
    cp.created = when.replace(tzinfo=None)
    cp.modified = when.replace(tzinfo=None)

    input_sha = sha256_file(deck_path)
    template_sha = sha256_file(brand.template)
    props = {
        "deck-builder:engine": __version__,
        "deck-builder:brand": brand.slug,
        "deck-builder:brand-version": brand.version,
        "deck-builder:template-sha256": template_sha,
        "deck-builder:input-sha256": input_sha,
    }
    buf = io.BytesIO()
    prs.save(buf)
    blob = normalize(buf.getvalue(), when.strftime("%Y-%m-%dT%H:%M:%SZ"), props)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(blob)

    manifest = {
        "engine": __version__,
        "brand": {"slug": brand.slug, "version": brand.version, "template_sha256": template_sha},
        "input": {"file": deck_path.name, "sha256": input_sha},
        "output": {"file": out_path.name, "sha256": hashlib.sha256(blob).hexdigest(),
                   "content_sha256": content_digest(blob)},
        "slides": slides,
    }
    manifest_path(out_path).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest, b.issues


def manifest_path(out_path: Path) -> Path:
    return out_path.with_name(out_path.stem + ".manifest.json")
