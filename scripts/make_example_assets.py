"""Draw the neutral brand's logo and icons and the example deck's image. Run by hand; outputs are committed.

    uv run python scripts/make_example_assets.py

Icons are alpha masks (black on transparent), which the engine recolors at build time.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DATA = Path(__file__).resolve().parent.parent / "src" / "deck_builder" / "data"
NEUTRAL = DATA / "brands" / "neutral" / "assets"
DECKS = DATA / "decks"
SIZE = 256
INK = (0, 0, 0, 255)


def icon(name: str, draw_fn) -> None:  # type: ignore[no-untyped-def]
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im))
    (NEUTRAL / "icons").mkdir(parents=True, exist_ok=True)
    im.save(NEUTRAL / "icons" / f"{name}.png")


def main() -> None:
    icon("check", lambda d: d.line([(48, 136), (104, 192), (208, 72)], fill=INK, width=28, joint="curve"))
    icon("arrow", lambda d: (d.line([(40, 128), (196, 128)], fill=INK, width=28),
                             d.polygon([(160, 64), (224, 128), (160, 192)], fill=INK)))
    icon("star", lambda d: d.polygon([(128, 24), (156, 100), (236, 100), (172, 148), (196, 228), (128, 180),
                                      (60, 228), (84, 148), (20, 100), (100, 100)], fill=INK))
    icon("chart", lambda d: [d.rectangle(box, fill=INK) for box in
                             ((40, 150, 84, 220), (106, 100, 150, 220), (172, 48, 216, 220))])
    icon("people", lambda d: (d.ellipse((88, 32, 168, 112), fill=INK),
                              d.pieslice((40, 124, 216, 300), 180, 360, fill=INK)))
    icon("clock", lambda d: (d.ellipse((24, 24, 232, 232), outline=INK, width=24),
                             d.line([(128, 128), (128, 64)], fill=INK, width=20),
                             d.line([(128, 128), (176, 156)], fill=INK, width=20)))

    logo = Image.new("RGBA", (720, 240), (0, 0, 0, 0))
    d = ImageDraw.Draw(logo)
    d.rounded_rectangle((0, 20, 200, 220), radius=40, fill=(47, 62, 77, 255))
    font = ImageFont.load_default(size=96)
    d.text((236, 70), "Logo", fill=(47, 62, 77, 255), font=font)
    logo.save(NEUTRAL / "logo.png")

    photo = Image.new("RGB", (1600, 1000))
    px = photo.load()
    for y in range(1000):
        for x in range(1600):
            px[x, y] = (40 + x * 60 // 1600, 70 + y * 80 // 1000, 110 + (x + y) * 60 // 2600)
    d = ImageDraw.Draw(photo)
    for i, x in enumerate(range(160, 1500, 260)):
        d.rectangle((x, 700 - i * 90, x + 160, 900), fill=(230, 232, 236))
    (DECKS / "quarterly-review" / "assets").mkdir(parents=True, exist_ok=True)
    photo.save(DECKS / "quarterly-review" / "assets" / "warehouse.png")


if __name__ == "__main__":
    main()
