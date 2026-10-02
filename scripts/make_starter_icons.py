"""Draw the engine's starter icons, which every brand can use. Run by hand; outputs are committed.

    uv run python scripts/make_starter_icons.py

`brand:icon/<id>` uses the brand's own icon when its kit has one, and the starter icon otherwise, so a
new kit can place icons before it has any. Icons are alpha masks (black on transparent), recolored at
build time, drawn here from simple shapes so they carry no third-party license.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "src" / "deck_builder" / "data" / "icons"
SIZE = 256
INK = (0, 0, 0, 255)
CLEAR = (0, 0, 0, 0)  # drawn over ink, it cuts a gap


def _check(d: ImageDraw.ImageDraw) -> None:
    d.line([(48, 136), (104, 192), (208, 72)], fill=INK, width=28, joint="curve")


def _arrow(d: ImageDraw.ImageDraw) -> None:
    d.line([(40, 128), (196, 128)], fill=INK, width=28)
    d.polygon([(160, 64), (224, 128), (160, 192)], fill=INK)


def _star(d: ImageDraw.ImageDraw) -> None:
    d.polygon([(128, 24), (156, 100), (236, 100), (172, 148), (196, 228), (128, 180), (60, 228), (84, 148),
               (20, 100), (100, 100)], fill=INK)


def _chart(d: ImageDraw.ImageDraw) -> None:
    for box in ((40, 150, 84, 220), (106, 100, 150, 220), (172, 48, 216, 220)):
        d.rectangle(box, fill=INK)


def _people(d: ImageDraw.ImageDraw) -> None:
    d.ellipse((88, 32, 168, 112), fill=INK)
    d.pieslice((40, 124, 216, 300), 180, 360, fill=INK)


def _clock(d: ImageDraw.ImageDraw) -> None:
    d.ellipse((24, 24, 232, 232), outline=INK, width=24)
    d.line([(128, 128), (128, 64)], fill=INK, width=20)
    d.line([(128, 128), (176, 156)], fill=INK, width=20)


def _database(d: ImageDraw.ImageDraw) -> None:
    for y in (32, 100, 168):
        d.rounded_rectangle((44, y, 212, y + 56), radius=28, fill=INK)


def _document(d: ImageDraw.ImageDraw) -> None:
    d.polygon([(64, 20), (156, 20), (204, 68), (204, 236), (64, 236)], fill=INK)
    d.polygon([(156, 20), (156, 68), (204, 68)], fill=CLEAR)
    for y in (112, 152, 192):
        d.line([(92, y), (176, y)], fill=CLEAR, width=14)


def _layers(d: ImageDraw.ImageDraw) -> None:
    for dy in (96, 48, 0):
        d.polygon([(128, 36 + dy), (228, 84 + dy), (128, 132 + dy), (28, 84 + dy)], fill=CLEAR)
        d.polygon([(128, 36 + dy), (228, 84 + dy), (128, 132 + dy), (28, 84 + dy)], outline=INK, width=18)


def _warning(d: ImageDraw.ImageDraw) -> None:
    d.polygon([(128, 20), (244, 228), (12, 228)], fill=INK)
    d.line([(128, 92), (128, 156)], fill=CLEAR, width=24)
    d.ellipse((114, 178, 142, 206), fill=CLEAR)


def _gear(d: ImageDraw.ImageDraw) -> None:
    for k in range(8):
        a = k * math.pi / 4
        pts = []
        for da, r in ((-0.22, 76), (-0.16, 116), (0.16, 116), (0.22, 76)):
            pts.append((128 + r * math.cos(a + da), 128 + r * math.sin(a + da)))
        d.polygon(pts, fill=INK)
    d.ellipse((44, 44, 212, 212), fill=INK)
    d.ellipse((96, 96, 160, 160), fill=CLEAR)


def _shield(d: ImageDraw.ImageDraw) -> None:
    d.polygon([(128, 20), (216, 52), (210, 140), (128, 236), (46, 140), (40, 52)], fill=INK)
    d.line([(88, 128), (118, 158), (172, 100)], fill=CLEAR, width=22, joint="curve")


ICONS: dict[str, Callable[[ImageDraw.ImageDraw], None]] = {
    "arrow": _arrow, "chart": _chart, "check": _check, "clock": _clock, "database": _database,
    "document": _document, "gear": _gear, "layers": _layers, "people": _people, "shield": _shield,
    "star": _star, "warning": _warning,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, draw in ICONS.items():
        im = Image.new("RGBA", (SIZE, SIZE), CLEAR)
        draw(ImageDraw.Draw(im))
        im.save(OUT / f"{name}.png")
    print(f"wrote {len(ICONS)} icons to {OUT}")


if __name__ == "__main__":
    main()
