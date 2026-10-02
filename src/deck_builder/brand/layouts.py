"""The layout sets `brand init` generates. Geometry is in inches on a margin grid, scaled to the slide size.

Placeholder idx values are part of the contract with tokens.yaml, so they never change for a layout key.
Type sizes here are the generator's documented design defaults; a user can restyle the template in
PowerPoint afterward, and `brand check` keeps the mapping honest.
"""
from __future__ import annotations

from dataclasses import dataclass

MARGIN = 0.6
TITLE_Y, TITLE_H = 0.45, 1.05
BODY_Y = 1.7
FOOTER = 0.8  # space kept clear at the bottom for the logo and slide furniture


@dataclass
class PH:
    """One placeholder of a generated layout: the field it fills, its kind, idx, box in inches and type style."""

    field: str
    kind: str  # title | body | pic | chart | tbl
    idx: int
    x: float
    y: float
    w: float
    h: float
    size: float | None = None  # points
    bullets: bool = False
    anchor: str = "t"  # t | ctr | b
    align: str | None = None  # ctr
    bold: bool = False
    italic: bool = False
    color: str | None = None  # a theme color: tx1, tx2, bg1, accent1 ...
    required: bool = False


@dataclass
class LayoutDef:
    key: str
    name: str
    description: str
    phs: list[PH]
    heading: str = "title"
    background: str | None = None  # theme color for a full-bleed background
    hide_master: bool = False


@dataclass
class Grid:
    w: float
    h: float
    m: float = MARGIN

    @property
    def cw(self) -> float:
        return self.w - 2 * self.m

    @property
    def body_h(self) -> float:
        return self.h - BODY_Y - FOOTER

    def cols(self, n: int, gap: float = 0.4) -> list[tuple[float, float]]:
        width = (self.cw - gap * (n - 1)) / n
        return [(self.m + i * (width + gap), width) for i in range(n)]


def _title(g: Grid) -> PH:
    return PH("title", "title", 0, g.m, TITLE_Y, g.cw, TITLE_H, size=30, anchor="b", required=True)


def _defs(g: Grid) -> dict[str, LayoutDef]:
    mid = g.h * 0.36
    two = g.cols(2)
    three = g.cols(3)
    four = g.cols(4)
    d: dict[str, LayoutDef] = {}

    def add(ld: LayoutDef) -> None:
        d[ld.key] = ld

    add(LayoutDef("title", "Title", "Opening slide: deck title and subtitle", [
        PH("title", "title", 0, g.m, mid - 0.4, g.cw, 1.6, size=44, anchor="b", bold=True, color="bg1",
           required=True),
        PH("subtitle", "body", 1, g.m, mid + 1.35, g.cw, 1.0, size=20, color="bg1"),
    ], background="tx2", hide_master=True))
    add(LayoutDef("section", "Section", "Divider between parts of the deck", [
        PH("kicker", "body", 1, g.m, mid - 0.2, g.cw, 0.5, size=16, color="bg1"),
        PH("title", "title", 0, g.m, mid + 0.35, g.cw, 1.4, size=40, anchor="t", bold=True, color="bg1",
           required=True),
    ], background="tx2", hide_master=True))
    add(LayoutDef("content", "Content", "A title and up to six bullets", [
        _title(g),
        PH("body", "body", 1, g.m, BODY_Y, g.cw, g.body_h, size=20, bullets=True),
    ]))
    add(LayoutDef("closing", "Closing", "Last slide: a thank-you or call to action and contact line", [
        PH("title", "title", 0, g.m, mid - 0.4, g.cw, 1.6, size=40, anchor="b", align="ctr", bold=True,
           color="bg1", required=True),
        PH("subtitle", "body", 1, g.m, mid + 1.35, g.cw, 1.0, size=20, align="ctr", color="bg1"),
    ], background="tx2", hide_master=True))
    add(LayoutDef("two-col", "Two Column", "Two lists side by side, such as before and after", [
        _title(g),
        PH("left", "body", 1, two[0][0], BODY_Y, two[0][1], g.body_h, size=18, bullets=True),
        PH("right", "body", 2, two[1][0], BODY_Y, two[1][1], g.body_h, size=18, bullets=True),
    ]))
    add(LayoutDef("big-number", "Big Number", "One number that carries the point, with a caption", [
        PH("number", "title", 0, g.m, 1.3, g.cw, 2.7, size=96, anchor="b", bold=True, color="tx2", required=True),
        PH("caption", "body", 1, g.m, 4.15, g.cw, 1.3, size=24, required=True),
    ], heading="number"))
    add(LayoutDef("chart", "Chart", "A title and one native chart", [
        _title(g),
        PH("chart", "chart", 1, g.m, BODY_Y, g.cw, g.body_h, required=True),
    ]))
    add(LayoutDef("table", "Table", "A title and one table", [
        _title(g),
        PH("table", "tbl", 1, g.m, BODY_Y, g.cw, g.body_h, required=True),
    ]))
    add(LayoutDef("image", "Image", "A title, one image and a caption", [
        _title(g),
        PH("image", "pic", 1, g.m, BODY_Y, g.cw * 0.64, g.body_h, required=True),
        PH("caption", "body", 2, g.m + g.cw * 0.64 + 0.4, BODY_Y, g.cw * 0.36 - 0.4, g.body_h, size=16),
    ]))
    add(LayoutDef("quote", "Quote", "A pull quote; the ## heading is the quote", [
        PH("quote", "body", 1, g.m + 0.8, 1.4, g.cw - 1.6, 3.6, size=32, anchor="ctr", italic=True,
           color="tx2", required=True),
        PH("attribution", "body", 2, g.m + 0.8, 5.15, g.cw - 1.6, 0.6, size=18),
    ], heading="quote"))
    add(LayoutDef("image-right", "Image Right", "Bullets on the left, an image on the right", [
        _title(g),
        PH("body", "body", 1, two[0][0], BODY_Y, two[0][1], g.body_h, size=18, bullets=True),
        PH("image", "pic", 2, two[1][0], BODY_Y, two[1][1], g.body_h, required=True),
    ]))
    icon_row = [_title(g)]
    for i, (x, w) in enumerate(three, start=1):
        icon_row.append(PH(f"icon{i}", "pic", 8 + 2 * i, x + (w - 1.1) / 2, BODY_Y + 0.2, 1.1, 1.1,
                           required=i == 1))
        icon_row.append(PH(f"text{i}", "body", 9 + 2 * i, x, BODY_Y + 1.55, w, g.body_h - 1.55, size=16,
                           align="ctr"))
    add(LayoutDef("icon-row", "Icon Row", "Three icons, each with a short line of text", icon_row))
    add(LayoutDef("comparison", "Comparison", "Two labeled lists side by side", [
        _title(g),
        PH("left-heading", "body", 1, two[0][0], BODY_Y, two[0][1], 0.6, size=20, bold=True),
        PH("left", "body", 2, two[0][0], BODY_Y + 0.7, two[0][1], g.body_h - 0.7, size=18, bullets=True),
        PH("right-heading", "body", 3, two[1][0], BODY_Y, two[1][1], 0.6, size=20, bold=True),
        PH("right", "body", 4, two[1][0], BODY_Y + 0.7, two[1][1], g.body_h - 0.7, size=18, bullets=True),
    ]))
    add(LayoutDef("agenda", "Agenda", "The deck's sections, in order", [
        _title(g),
        PH("body", "body", 1, g.m, BODY_Y, g.cw, g.body_h, size=24, bullets=True),
    ]))
    team = [_title(g)]
    for i, (x, w) in enumerate(four, start=1):
        side = min(w, 2.0)
        team.append(PH(f"photo{i}", "pic", 8 + 2 * i, x + (w - side) / 2, BODY_Y + 0.1, side, side))
        team.append(PH(f"name{i}", "body", 9 + 2 * i, x, BODY_Y + side + 0.25, w, 1.0, size=16, align="ctr"))
    add(LayoutDef("team", "Team", "Up to four people with photos and names", team))
    return d


SETS = {
    "minimal": ["title", "section", "content", "closing"],
    "standard": ["title", "section", "content", "two-col", "big-number", "chart", "table", "image", "quote",
                 "closing"],
    "full": ["title", "section", "agenda", "content", "two-col", "comparison", "big-number", "chart", "table",
             "image", "image-right", "icon-row", "team", "quote", "closing"],
}


def layout_set(name: str, width_in: float, height_in: float) -> list[LayoutDef]:
    defs = _defs(Grid(width_in, height_in))
    return [defs[k] for k in SETS[name]]
