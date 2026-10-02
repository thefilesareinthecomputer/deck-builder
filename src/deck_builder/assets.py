"""Asset hashing and derived assets (recolored icons), cached by content."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from PIL import Image as PILImage


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _image_entry(asset_id: str, cls: str, path: Path, base: Path) -> dict[str, Any]:
    entry: dict[str, Any] = {"id": asset_id, "class": cls, "path": str(path.relative_to(base))
                             if path.is_relative_to(base) else str(path)}
    if path.is_file():
        entry["sha256"] = sha256_file(path)
        with PILImage.open(path) as im:
            entry["pixels"] = list(im.size)
    else:
        entry["missing"] = True
    return entry


def inventory_brand(brand: Any) -> list[dict[str, Any]]:
    """Every asset a brand declares: palette colors, fonts, logos, icons."""
    out: list[dict[str, Any]] = []
    for name, hexv in (brand.meta.get("palette") or {}).items():
        out.append({"id": name, "class": "color", "value": str(hexv).lstrip("#").upper()})
    for role, font in (brand.meta.get("fonts") or {}).items():
        out.append({"id": role, "class": "font", "value": font.get("family"), "fallback": font.get("fallback")})
    for lid, rel in (brand.meta.get("logos") or {}).items():
        out.append({**_image_entry(f"brand:logo/{lid}", "logo", brand.path / rel, brand.path)})
    icons = brand.meta.get("icons") or {}
    if icons.get("dir") and (brand.path / icons["dir"]).is_dir():
        for p in sorted((brand.path / icons["dir"]).glob("*.png")):
            entry = _image_entry(f"brand:icon/{p.stem}", "icon", p, brand.path)
            if icons.get("source"):
                entry["source"] = icons["source"]
            out.append(entry)
    return out


def inventory_deck(deck: Any, brand: Any, deck_dir: Path) -> list[dict[str, Any]]:
    """Every asset a deck references, with the slides that use it."""
    from deck_builder.model import Icon, Image
    from deck_builder.validate import resolve_asset

    used: dict[str, list[int]] = {}
    for n, s in enumerate(deck.slides, start=1):
        for val in s.fields.values():
            if isinstance(val, Image | Icon):
                used.setdefault(val.ref, []).append(n)
            elif isinstance(val, str) and val.startswith("brand:"):
                used.setdefault(val.strip(), []).append(n)
    out = []
    for ref, slides in sorted(used.items()):
        path, err = resolve_asset(ref, brand, deck_dir)
        cls = "logo" if ref.startswith("brand:logo/") else "icon" if ref.startswith("brand:icon/") else "image"
        if err or path is None:
            out.append({"id": ref, "class": cls, "unknown": True, "slides": slides})
            continue
        out.append({**_image_entry(ref, cls, path, brand.path if ref.startswith("brand:") else deck_dir),
                    "slides": slides})
    return out


def recolor_icon(src: Path, hex_color: str, cache_dir: Path) -> Path:
    """Fill an icon's alpha mask with one color. Same source and color give the same file."""
    key = hashlib.sha256(src.read_bytes() + hex_color.upper().encode()).hexdigest()
    out = cache_dir / f"{key}.png"
    if out.is_file():
        return out
    cache_dir.mkdir(parents=True, exist_ok=True)
    with PILImage.open(src) as im:
        alpha = im.convert("RGBA").getchannel("A")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    filled = PILImage.new("RGBA", alpha.size, (r, g, b, 255))
    filled.putalpha(alpha)
    tmp = out.with_suffix(".tmp")
    filled.save(tmp, format="PNG", optimize=False)
    tmp.replace(out)
    return out
