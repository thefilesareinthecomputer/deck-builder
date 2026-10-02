"""PDF pages -> slide PNGs, and slide PNGs -> contact sheets sized to stay cheap for an agent to view."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from deck_builder.errors import EnvError
from deck_builder.qa import tools

# An image's token cost grows with its area up to about 1.15 megapixels, where viewers downscale it.
# A sheet of 20 thumbnails at this size costs about as much as one full slide.
TILE_W = 360
COLS = 4
PAD, LABEL = 10, 22


def rasterize(pdf: Path, out_dir: Path, size: tuple[int, int], pages: list[int] | None, total: int) -> list[Path]:
    """size is the exact PNG size in pixels; renderers' PDF page sizes can be a fraction of a point off."""
    missing = tools.poppler_missing()
    if missing:
        raise EnvError(f"poppler isn't installed ({', '.join(missing)} missing): {tools.install_hint('poppler')}")
    width = max(2, len(str(total)))
    wanted = pages or list(range(1, total + 1))
    out = []
    for n in wanted:
        prefix = out_dir / f"page-{n}"
        subprocess.run(["pdftoppm", "-png", "-scale-to-x", str(size[0]), "-scale-to-y", str(size[1]), "-f", str(n),
                        "-l", str(n), "-singlefile", str(pdf.resolve()), str(prefix.resolve())], check=True,
                       capture_output=True,
                       timeout=120)
        target = out_dir / f"slide-{n:0{width}d}.png"
        prefix.with_suffix(".png").replace(target)
        out.append(target)
    return out


def contact_sheets(pngs: list[Path], out_dir: Path, batch: int, flagged: set[int]) -> list[Path]:
    """One sheet per batch of slides; flagged slides get a red frame and label."""
    sheets = []
    for b, start in enumerate(range(0, len(pngs), batch), start=1):
        group = pngs[start : start + batch]
        thumbs = []
        for p in group:
            with Image.open(p) as im:
                h = round(im.height * TILE_W / im.width)
                thumbs.append((p, im.convert("RGB").resize((TILE_W, h))))
        th = thumbs[0][1].height
        cols = min(COLS, len(thumbs))
        rows = -(-len(thumbs) // cols)
        sheet = Image.new("RGB", (cols * (TILE_W + PAD) + PAD, rows * (th + PAD + LABEL) + PAD), "#d1d5db")
        draw = ImageDraw.Draw(sheet)
        for i, (p, thumb) in enumerate(thumbs):
            n = int(p.stem.split("-")[-1])
            x = PAD + (i % cols) * (TILE_W + PAD)
            y = PAD + (i // cols) * (th + PAD + LABEL)
            bad = n in flagged
            draw.text((x, y + 4), f"slide {n}" + ("  FLAGGED" if bad else ""), fill="#b91c1c" if bad else "#111827")
            sheet.paste(thumb, (x, y + LABEL))
            if bad:
                draw.rectangle((x - 3, y + LABEL - 3, x + TILE_W + 2, y + LABEL + th + 2), outline="#dc2626", width=3)
        path = out_dir / f"contact-{b:02d}.png"
        sheet.save(path)
        sheets.append(path)
    return sheets
