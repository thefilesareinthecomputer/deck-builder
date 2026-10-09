"""Regenerate the README images from the demo-brand fixtures: `uv run python scripts/readme_images.py`.

Generates three dark kits from the Cubicle 9 demo brand (its fonts and layouts, a dark palette each), renders
slides from its review deck and the showcase deck in them with LibreOffice at twice the default resolution, and
writes docs/images/hero.png (three review slides in the blue kit, fanned) and docs/images/brands.png (the
showcase's chart slide, the README example's third slide, in the three kits, fanned), each on a dark panel.
Run it after any change to the generator, the layouts or the renderer, and commit the images with that change.
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
import tempfile
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter

from deck_builder.cli import main as cli

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures" / "demo-brands"
BASE = "cubicle-nine"  # the demo brand the dark kits take their fonts, layouts and assets from
# The dark kits' palettes: one neutral near-black ground with a standard accent each. Text on a primary-color
# fill takes the background color, so each primary is light enough for dark text, and a light gray accent keeps
# a chart's second series neutral.
NEUTRALS = {"ink": "E6EDF3", "muted": "8B949E", "surface": "161B22", "background": "0D1117"}
DARK = {
    "dark-mono": {**NEUTRALS, "primary": "E6EDF3", "accent": "8B949E", "muted": "6E7681"},
    "dark-teal": {**NEUTRALS, "primary": "2DD4BF", "accent": "C9D1D9"},
    "dark-blue": {**NEUTRALS, "primary": "58A6FF", "accent": "C9D1D9"},
}
BRANDS = ("dark-mono", "dark-teal", "dark-blue")  # brands.png back to front, the hero's kit in front
CHART = 4  # the showcase's chart slide
HERO = (11, 13, 5)  # review-deck slides in the blue kit, back to front: a table, three changes, a line chart
PANEL = ("161B22", "0D1117")  # the panel's gradient, top to bottom
DPI = "192"
RATIO = 9 / 16  # slide height over width
RADIUS = 14


def run(*argv: str) -> None:
    code = cli(list(argv))
    if code != 0:
        sys.exit(f"deck-builder {' '.join(argv)} exited {code}")


def dark_kit(slug: str, tmp: Path) -> Path:
    """A copy of the base brand's folder with a dark palette, ready for `brand init --from`."""
    folder = tmp / "src" / slug
    shutil.copytree(FIXTURES / "brands" / BASE, folder)
    brand = yaml.safe_load((folder / "brand.yaml").read_text())
    brand["slug"] = slug
    brand["palette"] = DARK[slug]
    brand["theme_colors"].update({"accent4": "3FB950", "accent5": "D29922", "accent6": "A371F7", "hlink": "accent"})
    brand["fonts"]["body"] = dict(brand["fonts"]["heading"])
    brand["icons"]["default_color"] = "primary"
    brand["generate"].pop("logo_on_master", None)  # the logos are drawn for a light background
    brand["generate"]["code"] = {"theme": "dark"}
    (folder / "brand.yaml").write_text(yaml.safe_dump(brand, sort_keys=False))
    return folder / "brand.yaml"


def card(png: Path, width: int) -> Image.Image:
    """The slide at width, with rounded corners and a faint light edge, on a transparent ground."""
    size = (width, round(width * RATIO))
    with Image.open(png) as src:
        im = src.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), RADIUS, fill=255)
    ImageDraw.Draw(im).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), RADIUS, outline=(255, 255, 255, 34),
                                         width=2)
    im.putalpha(mask)
    return im


def panel(size: tuple[int, int], radius: int = 28) -> Image.Image:
    """A dark vertical gradient with rounded corners."""
    top, bottom = (tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) for c in PANEL)
    strip = Image.new("RGBA", (1, size[1]))
    for y in range(size[1]):
        t = y / (size[1] - 1)
        strip.putpixel((0, y), (*(round(a + (b - a) * t) for a, b in zip(top, bottom, strict=True)), 255))
    canvas = strip.resize(size)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    canvas.putalpha(mask)
    return canvas


def place(canvas: Image.Image, im: Image.Image, xy: tuple[int, int], blur: int = 30) -> None:
    """im on the canvas at xy, over a dark shadow."""
    alpha = Image.new("L", canvas.size, 0)
    alpha.paste(im.getchannel("A").point(lambda a: round(a * 0.55)), (xy[0], xy[1] + blur // 3))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(blur)))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(im, xy)


def fan(slides: list[Path], out: Path, width: int = 1500, step: tuple[int, int] = (380, 90), margin: int = 64) -> None:
    """Slides overlapping down and to the right on a dark panel, the last one in front and whole."""
    n = len(slides)
    canvas = panel((2 * margin + width + step[0] * (n - 1), 2 * margin + round(width * RATIO) + step[1] * (n - 1)))
    for i, png in enumerate(slides):
        place(canvas, card(png, width), (margin + i * step[0], margin + i * step[1]))
    canvas.save(out, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(REPO / "docs" / "images"), help="folder for the images")
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        config = str(Path(tmp, "deck-builder.toml"))
        run("init", "--dir", tmp)
        for slug in BRANDS:
            run("--config", config, "brand", "init", slug, "--from", str(dark_kit(slug, Path(tmp))))
        built = Path(tmp, "built")
        # The showcase deck, one build per kit: the first data row (the README example's), with the kit as brand
        # and the base brand's photo under the kit's name.
        showcase = Path(tmp, "showcase")
        shutil.copytree(FIXTURES / "showcase", showcase)
        for slug in BRANDS:
            shutil.copyfile(showcase / "assets" / f"{BASE}-hero.png", showcase / "assets" / f"{slug}-hero.png")
        with open(showcase / "brands.csv", newline="") as f:
            rows = list(csv.DictReader(f))
        with open(showcase / "dark.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows({**rows[0], "brand": slug} for slug in BRANDS)
        run("--config", config, "build", str(showcase / "deck.md"), "--data", str(showcase / "dark.csv"),
            "--name", "{{brand}}.pptx", "-o", str(built))
        for slug in BRANDS:
            run("--config", config, "render", str(built / f"{slug}.pptx"), "--slides", str(CHART),
                "--backend", "libreoffice", "--dpi", DPI)
        fan([built / f"{slug}.render" / f"slide-{CHART:02d}.png" for slug in BRANDS], out / "brands.png")
        review = built / "review.pptx"
        run("--config", config, "build", str(FIXTURES / "decks" / BASE / "review" / "deck.md"), "--brand", BRANDS[-1],
            "-o", str(review))
        run("--config", config, "render", str(review), "--slides", ",".join(map(str, HERO)),
            "--backend", "libreoffice", "--dpi", DPI)
        fan([built / "review.render" / f"slide-{n:02d}.png" for n in HERO], out / "hero.png")
    print(f"wrote {out / 'hero.png'} and {out / 'brands.png'}")


if __name__ == "__main__":
    main()
