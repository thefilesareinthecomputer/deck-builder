"""Build a resolved deck into a PPTX and its manifest."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn

from deck_builder import __version__
from deck_builder import template as tpl
from deck_builder.assets import recolor_icon, sha256_file
from deck_builder.brand.registry import Brand
from deck_builder.build.normalize import content_digest, normalize
from deck_builder.build.text import CODE_FONT_DEFAULT, fill_text
from deck_builder.build.visuals import fill_chart, fill_picture, fill_table
from deck_builder.errors import EnvError, Issue
from deck_builder.model import Chart, Deck, Icon, Image, Slide, Table
from deck_builder.validate import plain, resolve_asset, text_of

EMU_PER_INCH = 914400
MIN_DPI = 150
DEFAULT_DATE = dt.date(2000, 1, 1)
SLIDENUM_FIELD = "{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}"  # used when the layout's field has no usable id
FIELD_ID = re.compile(r"\{[0-9A-Fa-f-]{36}\}")
OFF = {"false", "no", "off", "0"}


def furniture_settings(meta: dict[str, Any]) -> tuple[bool, str | None]:
    """(slide numbers on, footer text) from front matter: `slide_numbers: false` and `footer: <text>`."""
    numbers = str(meta.get("slide_numbers", True)).strip().lower() not in OFF
    footer = str(meta["footer"]).strip() if meta.get("footer") not in (None, "") else None
    return numbers, footer or None


def add_furniture(slide: Any, layout: Any, n: int, numbers: bool, footer: str | None) -> None:
    """Copy the layout's slide-number placeholder (and its footer when there's text for it) onto the slide.

    python-pptx never copies these. The whole placeholder is copied, so the template's position and
    styling stay as they are (LibreOffice doesn't inherit them), and only its text is replaced. Dates
    are never copied.
    """
    tree = slide.shapes._spTree
    ids = [str(e.get("id", "")) for e in tree.iter(qn("p:cNvPr"))]
    next_id = max((int(i) for i in ids if i.isdigit()), default=1) + 1
    for ph in layout.placeholders:
        kind = ph.placeholder_format.type
        if kind == PP_PLACEHOLDER.SLIDE_NUMBER and numbers:
            fld = ph._element.find(f".//{qn('a:fld')}[@type='slidenum']")
            fid = str(fld.get("id")) if fld is not None else ""
            fid = fid if FIELD_ID.fullmatch(fid) else SLIDENUM_FIELD  # an adopted template is untrusted XML
            para = f'<a:fld id="{fid}" type="slidenum"><a:rPr lang="en-US"/><a:t>{n}</a:t></a:fld>'
        elif kind == PP_PLACEHOLDER.FOOTER and footer:
            para = f'<a:r><a:rPr lang="en-US"/><a:t>{escape(footer)}</a:t></a:r>'
        else:
            continue
        sp = copy.deepcopy(ph._element)
        sp.find(f"{qn('p:nvSpPr')}/{qn('p:cNvPr')}").set("id", str(next_id))
        next_id += 1
        body = sp.find(qn("p:txBody"))
        for p in body.findall(qn("a:p")):
            body.remove(p)
        body.append(parse_xml(f'<a:p {nsdecls("a")}>{para}</a:p>'))
        tree.append(sp)


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
    def __init__(self, brand: Brand, deck_dir: Path, cache_dir: Path, numbers: bool = True,
                 footer: str | None = None) -> None:
        self.brand = brand
        self.deck_dir = deck_dir
        self.cache_dir = cache_dir
        self.numbers, self.footer = numbers, footer
        self.code_font = (brand.tokens.get("text") or {}).get("code_font", CODE_FONT_DEFAULT)
        self.issues: list[Issue] = []

    def _picture(self, slide: Any, ph: Any, ref: str, alt: str, at: dict[str, Any],
                 fentry: dict[str, Any], color: str | None) -> None:
        path, _ = resolve_asset(ref, self.brand, self.deck_dir)
        assert path is not None  # validation guarantees it resolves
        brand_asset = ref.startswith("brand:")
        source = (path.resolve().relative_to(self.brand.path.resolve()) if brand_asset
                  else path.resolve().relative_to(self.deck_dir.resolve()))  # validation confines both
        if color:
            path = recolor_icon(path, color, self.cache_dir)
        geo = fill_picture(slide, ph, path, alt, crop=not brand_asset)
        fentry["asset"] = {"ref": ref, "source": source.as_posix(), "sha256": sha256_file(path)}
        if _dpi(path, geo, crop=not brand_asset) < MIN_DPI:
            self.issues.append(Issue("ASSET_LOW_RES", f"{ref!r} shows below {MIN_DPI} DPI at this size",
                                     severity="warning", **at))

    def slide(self, prs: Any, layouts: dict[Any, Any], s: Slide, n: int) -> dict[str, Any]:
        ls = self.brand.tokens["layouts"][s.layout]
        tl = ls["template_layout"]
        layout = tpl.find_layout(layouts, tl, ls.get("master"))
        slide = prs.slides.add_slide(layout)
        phs = {ph.placeholder_format.idx: ph for ph in slide.placeholders}
        entry: dict[str, Any] = {"slide": n, "layout": s.layout, "template_layout": tl, "title": s.title,
                                 "fields": {}}
        used: set[int] = set()
        # Fill in the layout's declared field order, so the output doesn't depend on input order
        # (a workbook's columns can order fields differently than the markdown did).
        for name in [f for f in ls["fields"] if f in s.fields]:
            val = s.fields[name]
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
                fentry["shape"] = ph.name  # lets the render step name the field that overflowed
            entry["fields"][name] = fentry
        for idx, ph in phs.items():
            if idx not in used:  # no empty "Click to add text" boxes left behind
                ph._element.getparent().remove(ph._element)
        add_furniture(slide, layout, n, self.numbers, self.footer)
        if s.notes:
            slide.notes_slide.notes_text_frame.text = s.notes
            entry["notes_chars"] = len(s.notes)
        return entry


def build(deck: Deck, brand: Brand, deck_path: Path, out_path: Path, cache_dir: Path, content_sha: str,
          keep_template_slides: bool = False) -> tuple[dict[str, Any], list[Issue]]:
    """content_sha identifies the deck's content independent of its file format (see pipeline.content_sha)."""
    assert brand.template is not None
    if out_path.exists() and not manifest_path(out_path).is_file():
        raise EnvError(f"{out_path} exists and has no {manifest_path(out_path).name} beside it, so deck-builder "
                       "didn't build it; move it or write somewhere else")
    prs = tpl.open_template(brand.template)
    if not keep_template_slides:
        tpl.remove_all_slides(prs)
    layouts = tpl.layouts(prs)
    b = Builder(brand, deck_path.parent, cache_dir, *furniture_settings(deck.meta))
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
        "deck-builder:content-sha256": content_sha,
    }
    buf = io.BytesIO()
    prs.save(buf)
    blob = normalize(buf.getvalue(), when.strftime("%Y-%m-%dT%H:%M:%SZ"), props)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(blob)

    manifest = {
        "engine": __version__,
        "brand": {"slug": brand.slug, "version": brand.version, "template_sha256": template_sha},
        "input": {"file": deck_path.name, "sha256": input_sha, "content_sha256": content_sha},
        "output": {"file": out_path.name, "sha256": hashlib.sha256(blob).hexdigest(),
                   "content_sha256": content_digest(blob)},
        "slides": slides,
    }
    manifest_path(out_path).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest, b.issues


def manifest_path(out_path: Path) -> Path:
    return out_path.with_name(out_path.stem + ".manifest.json")
