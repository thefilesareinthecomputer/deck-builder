"""The images a slide names, the slots its layout has for them, and what a crop to fill takes from each.

A slide names an image in two ways: an image field (`![alt](path)` in a `### image` section), or a line
in its speaker notes that starts with `SCREENSHOT:` or `DIAGRAM:` (an image cue, such as
`SCREENSHOT: assets/screenshots/run.png | shows: the run page`), which marks an image the slide is
meant to show. check (IMAGE_NO_SLOT, IMAGE_CROPPED), build (fit or crop) and `assets --images` all read
them here, so the three never disagree.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image as PILImage

from deck_builder.model import Image, Slide, Value

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
CUE = re.compile(r"^\s*(?:[>*-]\s*)?(SCREENSHOT|DIAGRAM):\s*(.*)$", re.IGNORECASE)
FITS = ("contain", "cover")
MAX_CROP = 15  # percent of an image a crop to fill can take before check warns; brand.yaml lint.max_crop
CONTAIN_FOLDER = "screenshots"  # images in a folder of this name are contained by default, never cropped
CARRIED = ("title", "kicker", "subtitle", "takeaway")  # fields every content layout shares
WHOLE = "Image shown whole"  # the build's name for a contained picture, so `import` keeps `fit: contain`


@dataclass
class Cue:
    """One image cue in a slide's notes. path is its first `|` part when that names an image file."""

    kind: str  # screenshot | diagram
    path: str | None
    text: str


def cues(notes: str) -> list[Cue]:
    out = []
    for ln in notes.splitlines():
        m = CUE.match(ln)
        if not m:
            continue
        text = m.group(2).strip()
        first = text.split("|", 1)[0].strip().strip("`")
        path = first if first and PurePosixPath(first).suffix.lower() in IMAGE_EXT | {".svg"} else None
        out.append(Cue(m.group(1).lower(), path, text))
    return out


def photo_slots(fspecs: dict[str, Any]) -> list[str]:
    """A layout's fields that show an image at its own size: not icons, and not logo slots, which always fit."""
    return [k for k, f in fspecs.items() if f.get("kind") == "image" and not f.get("fit")]


def image_layouts(spec_layouts: dict[str, Any]) -> dict[str, int]:
    """Layout -> how many images it holds, for the layouts built around images: a required photo slot,
    and not a full-bleed splash, which is for one photo per deck."""
    out = {}
    for key, ls in spec_layouts.items():
        fspecs = ls.get("fields") or {}
        slots = photo_slots(fspecs)
        if not ls.get("bleed") and any(fspecs[k].get("required") for k in slots):
            out[key] = len(slots)
    return out


def named(s: Slide, fspecs: dict[str, Any]) -> int:
    """How many images a slide names: those its image fields show, plus those its notes name. A cue with
    no path counts as one of the shown images that no cue names, if there's one left over."""
    shown = {v.ref for k, v in s.fields.items() if isinstance(v, Image) and k in photo_slots(fspecs)}
    cs = cues(s.notes)
    paths = {c.path for c in cs if c.path}
    pathless = sum(1 for c in cs if not c.path)
    return len(shown | paths) + max(0, pathless - len(shown - paths))


def fit_mode(s: Slide, ref: str) -> str:
    """contain or cover for one of the slide's images: the slide's `fit:`, else contain for an image in a
    `screenshots/` folder or named by an image cue, so a screenshot or diagram never loses its edges."""
    if s.fit in FITS:
        return str(s.fit)
    if CONTAIN_FOLDER in PurePosixPath(ref.replace("\\", "/")).parts[:-1]:
        return "contain"
    return "contain" if any(c.path == ref for c in cues(s.notes)) else "cover"


def transparent(path: Path) -> bool:
    """Whether an image has transparent pixels: logos and icons do, photos and screenshots don't.
    Cropping a logo breaks its usage terms, so these are fitted inside the placeholder instead."""
    with PILImage.open(path) as im:
        if im.mode not in ("RGBA", "LA", "PA") and "transparency" not in im.info:
            return False
        low = im.convert("RGBA").getchannel("A").getextrema()[0]
        return isinstance(low, (int, float)) and low < 255


def crops(s: Slide, ref: str, fs: dict[str, Any], path: Path) -> bool:
    """Whether the build crops this image to fill its box: a photo does; a brand asset, a logo slot, an
    image with transparent pixels, or a contained image fits inside it."""
    return (not ref.startswith("brand:") and not fs.get("fit") and fit_mode(s, ref) == "cover"
            and not transparent(path))


def crop_loss(image_size: tuple[int, int], box: tuple[int, int]) -> tuple[float, str]:
    """(share of the image a centered crop to fill takes, the sides it comes from)."""
    (iw, ih), (bw, bh) = image_size, box
    if not iw or not ih or not bw or not bh:
        return 0.0, ""
    image, frame = iw / ih, bw / bh
    if image > frame:
        return 1 - frame / image, "left and right"
    return 1 - image / frame, "top and bottom"


def _text_items(value: Value) -> list[str]:
    from deck_builder.validate import plain

    if isinstance(value, list):
        return [plain(t) for _, t in value]
    return [plain(value)] if isinstance(value, str) and value.strip() else []


def move_cost(s: Slide, target: dict[str, Any]) -> str:
    """What moving a slide's content onto a target layout costs, said as the cuts to make: the heading,
    kicker, subtitle and takeaway stay where the target has them, the rest of the text goes into the
    target's other text fields, and anything else (a table, a chart, code, icons) is lost."""
    from deck_builder.model import kind_of

    tf = target.get("fields") or {}
    heading = target.get("heading_field") or "title"
    free = [k for k, f in tf.items() if f.get("kind") in ("text", "bullets") and k not in CARRIED and k != heading]
    moving: list[str] = []
    lost: list[str] = []
    for k, v in s.fields.items():
        if isinstance(v, Image) or v == s.title or (k in CARRIED and k in tf):
            continue  # the images are what the move is for, and the heading moves to the target's
        what = f"the {k}" if k in CARRIED else f"its {kind_of(v).replace('icon', 'icons')}"
        if isinstance(v, str | list) and k not in CARRIED:
            moving += _text_items(v)
        elif what not in lost:
            lost.append(what)
    items = sum((int(tf[k].get("max_bullets") or 1) if tf[k].get("kind") == "bullets" else 1) for k in free)
    chars = sum(int(tf[k].get("max_chars") or 0) for k in free)
    per = min((int(tf[k]["max_bullet_chars"]) for k in free if tf[k].get("max_bullet_chars")), default=0)
    cuts = []
    if moving and not free:
        lost.append("its text")
    elif moving:
        if len(moving) > items:
            cuts.append(f"cut {len(moving) - items} of {len(moving)} items")
        total = sum(len(t) for t in moving)
        if chars and total > chars:
            cuts.append(f"cut {total - chars} of {total} characters")
        if per and (long := sum(1 for t in moving if len(t) > per)):
            cuts.append(f"shorten {long} item{'s' * (long != 1)} to {per} characters")
    said = "; ".join([" and ".join(cuts)] * bool(cuts) + [f"drops {', '.join(lost)}"] * bool(lost))
    return said or "fits as is"
