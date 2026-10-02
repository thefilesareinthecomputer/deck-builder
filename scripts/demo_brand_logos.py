"""Redraw the demo brands' logo wordmarks from their SVG sources: `uv run python scripts/demo_brand_logos.py`.

Keeps each logo PNG's mark (everything left of the text) and redraws the wordmark and tagline from the
text, font, size, letter spacing and color in the brand's assets/svg/logo.svg and logo-mono.svg. Run it
after changing a demo brand's name in its SVGs, then commit the PNGs. macOS only: it uses the system's
Georgia, Avenir Next, Helvetica Neue and Arial.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BRANDS = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "demo-brands" / "brands"
FONTS = {
    ("Georgia", True): "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    ("Avenir Next", True): "/System/Library/Fonts/Avenir Next.ttc",
    ("Helvetica Neue", True): "/System/Library/Fonts/HelveticaNeue.ttc",
    ("Arial", False): "/System/Library/Fonts/Supplemental/Arial.ttf",
}
TEXT = re.compile(r'<text x="([\d.]+)" y="([\d.]+)" font-family="([^"]+)" font-size="([\d.]+)"'
                  r'(?: font-weight="(\d+)")?(?: letter-spacing="([\d.]+)")? fill="#([0-9A-Fa-f]{6})">([^<]*)</text>')


def font(family: str, size: float, bold: bool) -> ImageFont.FreeTypeFont:
    """The family's bold or regular face; a .ttc collection is searched by style name."""
    path = FONTS[(family, bold)]
    want = {"Bold"} if bold else {"Regular", "Roman"}
    for index in range(32):
        try:
            face = ImageFont.truetype(path, size, index=index)
        except OSError:
            break
        if face.getname()[1] in want:
            return face
    return ImageFont.truetype(path, size)


def redraw(svg_path: Path, png_path: Path) -> None:
    svg = svg_path.read_text(encoding="utf-8")
    im = Image.open(png_path).convert("RGBA")
    width = re.search(r'width="([\d.]+)"', svg)
    scale = im.width / float(width.group(1)) if width else 1.0
    texts = TEXT.findall(svg)
    left = int(min(float(t[0]) for t in texts) * scale) - 12
    im.paste((0, 0, 0, 0), (left, 0, im.width, im.height))  # clear the old wordmark, keep the mark
    draw = ImageDraw.Draw(im)
    for x, y, family, size, weight, spacing, color, text in texts:
        face = font(family, float(size) * scale, weight == "700")
        fill = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
        cx, cy = float(x) * scale, float(y) * scale
        gap = float(spacing or 0) * scale
        for ch in text if gap else [text]:
            draw.text((cx, cy), ch, font=face, fill=fill, anchor="ls")
            cx += draw.textlength(ch, font=face) + gap
    im.save(png_path)


def main() -> None:
    for brand in sorted(p for p in BRANDS.iterdir() if p.is_dir()):
        for name in ("logo", "logo-mono"):
            redraw(brand / "assets" / "svg" / f"{name}.svg", brand / "assets" / f"{name}.png")
            print(f"redrew {brand.name}/assets/{name}.png")


if __name__ == "__main__":
    main()
