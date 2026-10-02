"""Asset hashing and derived assets (recolored icons), cached by content."""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image as PILImage


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
