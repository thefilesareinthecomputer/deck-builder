"""Regenerate the README images from the demo-brand fixtures: `uv run python scripts/readme_images.py`.

Builds the showcase deck in the three demo brands and a few slides from their pitch decks, renders them with
LibreOffice at twice the default resolution, and writes docs/images/hero.png (a large chart slide beside an image
slide and a process slide, one brand each) and docs/images/brands.png (the showcase's cards slide, the README
example's second slide, in the three brands, fanned). Run it after any change to the generator, the layouts or
the renderer, and commit the images with that change.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from deck_builder.cli import main as cli

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures" / "demo-brands"
BRANDS = ("cubicle-nine", "soap-club", "dumbder-nifftlin")  # brands.png back to front, the README example's in front
CARDS = 3  # the showcase's cards slide
# hero.png: (brand, deck, slide) for the large slide, then the two stacked beside it
HERO = (("dumbder-nifftlin", "pitch", 4), ("soap-club", "pitch", 5), ("cubicle-nine", "pitch", 5))
DPI = "192"
RATIO = 9 / 16  # slide height over width
RADIUS = 18
SHADOW = 28


def run(*argv: str) -> None:
    code = cli(list(argv))
    if code != 0:
        sys.exit(f"deck-builder {' '.join(argv)} exited {code}")


def card(png: Path, width: int) -> Image.Image:
    """The slide at width, with rounded corners and a hairline edge, on a transparent ground."""
    size = (width, round(width * RATIO))
    with Image.open(png) as im:
        im = im.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), RADIUS, fill=255)
    ImageDraw.Draw(im).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), RADIUS, outline=(0, 0, 0, 40), width=2)
    im.putalpha(mask)
    return im


def place(canvas: Image.Image, im: Image.Image, xy: tuple[int, int]) -> None:
    """im on the canvas at xy, over a soft shadow."""
    alpha = Image.new("L", canvas.size, 0)
    alpha.paste(im.getchannel("A").point(lambda a: round(a * 0.22)), (xy[0], xy[1] + SHADOW // 2))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(SHADOW)))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(im, xy)


def hero(big: Path, top: Path, bottom: Path, out: Path, small: int = 760, gap: int = 40) -> None:
    """One large slide with two smaller ones stacked to its right, the same height."""
    pad = 2 * SHADOW
    small_h = round(small * RATIO)
    big_w = round((2 * small_h + gap) / RATIO)
    canvas = Image.new("RGBA", (2 * pad + big_w + gap + small, 2 * pad + 2 * small_h + gap))
    place(canvas, card(big, big_w), (pad, pad))
    place(canvas, card(top, small), (pad + big_w + gap, pad))
    place(canvas, card(bottom, small), (pad + big_w + gap, pad + small_h + gap))
    canvas.save(out, optimize=True)


def fan(slides: list[Path], out: Path, width: int = 1300, step: int = 520) -> None:
    """Slides overlapping left to right, the last one in front and whole."""
    pad = 2 * SHADOW
    canvas = Image.new("RGBA", (2 * pad + width + step * (len(slides) - 1), 2 * pad + round(width * RATIO)))
    for i, png in enumerate(slides):
        place(canvas, card(png, width), (pad + i * step, pad))
    canvas.save(out, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(REPO / "docs" / "images"), help="folder for the images")
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        config = str(Path(tmp, "deck-builder.toml"))
        run("init", "--dir", tmp)
        for brand in BRANDS:
            run("--config", config, "brand", "init", brand, "--from", str(FIXTURES / "brands" / brand / "brand.yaml"))
        built = Path(tmp, "built")
        run("--config", config, "build", str(FIXTURES / "showcase" / "deck.md"),
            "--data", str(FIXTURES / "showcase" / "brands.csv"), "--name", "{{brand}}.pptx", "-o", str(built))
        for brand in BRANDS:
            run("--config", config, "render", str(built / f"{brand}.pptx"), "--slides", str(CARDS),
                "--backend", "libreoffice", "--dpi", DPI)
        fan([built / f"{b}.render" / f"slide-{CARDS:02d}.png" for b in BRANDS], out / "brands.png")
        for brand, deck, n in HERO:
            pptx = built / "decks" / f"{brand}-{deck}.pptx"
            run("--config", config, "build", str(FIXTURES / "decks" / brand / deck / "deck.md"), "-o", str(pptx))
            run("--config", config, "render", str(pptx), "--slides", str(n), "--backend", "libreoffice", "--dpi", DPI)
        big, top, bottom = (built / "decks" / f"{b}-{d}.render" / f"slide-{n:02d}.png" for b, d, n in HERO)
        hero(big, top, bottom, out / "hero.png")
    print(f"wrote {out / 'hero.png'} and {out / 'brands.png'}")


if __name__ == "__main__":
    main()
