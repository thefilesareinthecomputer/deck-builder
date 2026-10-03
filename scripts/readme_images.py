"""Regenerate the README images from the demo-brand fixtures: `uv run python scripts/readme_images.py`.

Builds tests/fixtures/demo-brands/showcase/deck.md and the nine decks in decks/ into the demo brands,
renders them with LibreOffice, and writes docs/images/decks.png (one slide from each of the nine decks),
docs/images/showcase.png (one deck in three brands, a column per brand) and docs/images/contact-sheet.png
(one brand's contact sheet, the review surface). Run it after any
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
BRANDS = ("dumbder-nifftlin", "cubicle-nine", "soap-club")
ROWS = (1, 3, 4)  # the title, cards and chart slides of the showcase deck
CONTACT_BRAND = "dumbder-nifftlin"  # the brand the README's deck.md example uses
# decks.png, the README's first image: one slide from each of the nine brand decks, a column per brand and
# a row per deck, picked so no two cells share a layout.
DECKS = ("pitch", "review", "edge")
PICKS = {
    ("dumbder-nifftlin", "pitch"): 5, ("cubicle-nine", "pitch"): 4, ("soap-club", "pitch"): 2,
    ("dumbder-nifftlin", "review"): 12, ("cubicle-nine", "review"): 10, ("soap-club", "review"): 4,
    ("dumbder-nifftlin", "edge"): 4, ("cubicle-nine", "edge"): 12, ("soap-club", "edge"): 10,
}
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


def grid(cells: list[list[Path]], out: Path) -> None:
    """Slide images in rows and columns, rounded, on a transparent ground."""
    rows, cols = len(cells), len(cells[0])
    canvas = Image.new("RGBA", (cols * SLIDE[0] + (cols - 1) * GAP, rows * SLIDE[1] + (rows - 1) * GAP))
    for r, row in enumerate(cells):
        for c, png in enumerate(row):
            with Image.open(png) as im:
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
        grid([[render_dirs[b] / f"slide-{n:02d}.png" for b in BRANDS] for n in ROWS], out / "showcase.png")
        shutil.copyfile(render_dirs[CONTACT_BRAND] / "contact-01.png", out / "contact-sheet.png")
        for brand in BRANDS:
            for deck in DECKS:
                pptx = built / "decks" / f"{brand}-{deck}.pptx"
                run("--config", config, "build", str(FIXTURES / "decks" / brand / deck / "deck.md"), "-o", str(pptx))
                run("--config", config, "render", str(pptx), "--slides", str(PICKS[brand, deck]),
                    "--backend", "libreoffice")
        grid([[built / "decks" / f"{b}-{d}.render" / f"slide-{PICKS[b, d]:02d}.png" for b in BRANDS] for d in DECKS],
             out / "decks.png")
    print(f"wrote {out / 'decks.png'}, {out / 'showcase.png'} and {out / 'contact-sheet.png'}")


if __name__ == "__main__":
    main()
