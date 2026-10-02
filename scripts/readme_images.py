"""Regenerate the README images from the demo-brand fixtures: `uv run python scripts/readme_images.py`.

Builds tests/fixtures/demo-brands/showcase/deck.md into each demo brand, renders it with LibreOffice,
and writes docs/images/showcase.png (three slides per brand, one column per brand) and
docs/images/contact-sheet.png (one brand's contact sheet, the review surface). Run it after any
change to the generator, the layouts or the renderer, and commit the images with that change.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from deck_builder.cli import main as cli

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures" / "demo-brands"
BRANDS = ("briarfield-paper", "cubicle-nine", "afterhours-soap")
ROWS = (1, 5, 7)  # title, chart and image slides of the showcase deck
SLIDE = (560, 315)
GAP = 24
RADIUS = 10


def run(*argv: str) -> None:
    code = cli(list(argv))
    if code != 0:
        sys.exit(f"deck-builder {' '.join(argv)} exited {code}")


def rounded(im: Image.Image) -> Image.Image:
    """The slide with rounded corners and a hairline edge, on a transparent ground."""
    im = im.convert("RGBA").resize(SLIDE, Image.Resampling.LANCZOS)
    mask = Image.new("L", SLIDE, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SLIDE[0] - 1, SLIDE[1] - 1), RADIUS, fill=255)
    ImageDraw.Draw(im).rounded_rectangle((0, 0, SLIDE[0] - 1, SLIDE[1] - 1), RADIUS, outline=(0, 0, 0, 36))
    im.putalpha(mask)
    return im


def showcase(render_dirs: dict[str, Path], out: Path) -> None:
    cols, rows = len(BRANDS), len(ROWS)
    canvas = Image.new("RGBA", (cols * SLIDE[0] + (cols - 1) * GAP, rows * SLIDE[1] + (rows - 1) * GAP))
    for c, brand in enumerate(BRANDS):
        for r, n in enumerate(ROWS):
            with Image.open(render_dirs[brand] / f"slide-{n:02d}.png") as im:
                canvas.alpha_composite(rounded(im), (c * (SLIDE[0] + GAP), r * (SLIDE[1] + GAP)))
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
            run("--config", config, "render", str(built / f"{brand}.pptx"), "--backend", "libreoffice")
        render_dirs = {b: built / f"{b}.render" for b in BRANDS}
        showcase(render_dirs, out / "showcase.png")
        shutil.copyfile(render_dirs["cubicle-nine"] / "contact-01.png", out / "contact-sheet.png")
    print(f"wrote {out / 'showcase.png'} and {out / 'contact-sheet.png'}")


if __name__ == "__main__":
    main()
