"""The layout sets `brand init` generates. Geometry is in inches on a margin grid, scaled to the slide size.

Placeholder idx values are part of the contract with tokens.yaml, so they never change for a layout key.
Type sizes come from a `Scale`, which `generate.type` in brand.yaml can override; a user can still restyle
the template in PowerPoint afterward, and `brand check` keeps the mapping honest.

Design rules the layouts follow (see `deck-builder docs design`): one title position on every content
slide; projected body text at 20 pt or more; sparse single-column content sits in the middle of the body
area instead of hugging the top; columns get structure (a tinted panel or a thin divider); one short
accent rule is the only decoration, used on title, section, closing and big-number slides.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

MARGIN = 0.6
TITLE_Y, TITLE_H = 0.45, 1.05
BODY_Y = 1.7
FOOTER = 0.8  # space kept clear at the bottom for the logo and slide furniture
RULE_W, RULE_H = 1.2, 0.07  # the accent rule
OPTICAL_LIFT = 0.3  # a centered body block sits this far above its area's middle, at the optical center
PANEL_PAD = 0.3


@dataclass(frozen=True)
class Scale:
    """Type sizes in points. Defaults are sized for a projected 16:9 deck."""

    title: float = 32
    title_bold: bool = True
    subtitle: float = 24
    body: float = 24
    two_col: float = 20
    icon_text: float = 18
    table: float = 16
    big_number: float = 120

    @classmethod
    def from_meta(cls, gen: dict[str, Any]) -> Scale:
        given = gen.get("type") or {}
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in given.items() if k in known})


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
    numbered: bool = False  # bullets become 1. 2. 3.
    anchor: str = "t"  # t | ctr | b
    align: str | None = None  # ctr
    bold: bool = False
    italic: bool = False
    color: str | None = None  # a theme color: tx1, tx2, bg1, accent1 ...
    required: bool = False
    fill: str | None = None  # a theme color behind the text: the box is drawn only when the field is used
    inset: float | None = None  # left and right text inset in inches, for a filled box
    lift: float = 0.0  # inches a centered body sits above its box's middle (written as a larger bottom inset)

    @property
    def text_h(self) -> float:
        """The height text can use: the box less the extra bottom inset that does the lift."""
        return self.h - 2 * self.lift


@dataclass
class Decor:
    """A drawn rectangle on a layout, behind its placeholders: a panel, a divider or the accent rule.

    fill is a theme color (bg2, accent2 ...) or a tint written "tx1@15": 15% of tx1 over the background.
    """

    x: float
    y: float
    w: float
    h: float
    fill: str


@dataclass
class LayoutDef:
    key: str
    name: str
    description: str
    phs: list[PH]
    heading: str = "title"
    background: str | None = None  # theme color for a full-bleed background
    hide_master: bool = False
    decor: list[Decor] = field(default_factory=list)


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


def _title(g: Grid, s: Scale) -> PH:
    return PH("title", "title", 0, g.m, TITLE_Y, g.cw, TITLE_H, size=s.title, anchor="b", bold=s.title_bold,
              required=True)


TAKEAWAY_Y, TAKEAWAY_H = 6.05, 0.55
BODY_END = TAKEAWAY_Y - 0.1  # bodies on layouts with a takeaway stop above it


def _takeaway(g: Grid) -> PH:
    """The optional so-what line: one sentence in a full-width band in the primary color."""
    return PH("takeaway", "body", 7, g.m, TAKEAWAY_Y, g.cw, TAKEAWAY_H, size=18, anchor="ctr", bold=True,
              color="bg1", fill="tx2", inset=0.2)


def _defs(g: Grid, s: Scale, body_anchor: str, big_number: str) -> dict[str, LayoutDef]:
    mid = g.h * 0.36
    two = g.cols(2)
    three = g.cols(3)
    four = g.cols(4)
    single = "ctr" if body_anchor == "middle" else "t"
    lift = OPTICAL_LIFT if body_anchor == "middle" else 0.0
    # Bodies end above the takeaway band, so short middle-anchored content centers at the optical
    # center, a little above the middle of the slide, rather than low in the body area.
    single_h = BODY_END - BODY_Y
    caption = max(14.0, s.two_col - 2)
    d: dict[str, LayoutDef] = {}

    def add(ld: LayoutDef) -> None:
        d[ld.key] = ld

    def rule(x: float, y: float) -> Decor:
        return Decor(x, y, RULE_W, RULE_H, "accent2")

    add(LayoutDef("title", "Title", "Opening slide: deck title and subtitle", [
        PH("title", "title", 0, g.m, mid - 0.6, g.cw, 1.7, size=44, anchor="b", bold=True, color="bg1",
           required=True),
        PH("subtitle", "body", 1, g.m, mid + 1.45, g.cw, 1.0, size=s.subtitle, color="bg1"),
    ], background="tx2", hide_master=True, decor=[rule(g.m + 0.1, mid + 1.25)]))
    add(LayoutDef("section", "Section", "Divider between parts of the deck", [
        PH("kicker", "body", 1, g.m, mid - 0.2, g.cw, 0.5, size=18, bold=True, color="accent2"),
        PH("title", "title", 0, g.m, mid + 0.35, g.cw, 1.4, size=40, anchor="t", bold=True, color="bg1",
           required=True),
    ], background="tx2", hide_master=True, decor=[rule(g.m + 0.1, mid - 0.45)]))
    add(LayoutDef("content", "Content", "A title and up to six bullets", [
        _title(g, s),
        PH("body", "body", 1, g.m, BODY_Y, g.cw, single_h, size=s.body, bullets=True, anchor=single, lift=lift),
        _takeaway(g),
    ]))
    add(LayoutDef("closing", "Closing", "Last slide: a thank-you or call to action and contact line", [
        PH("title", "title", 0, g.m, mid - 0.6, g.cw, 1.7, size=40, anchor="b", align="ctr", bold=True,
           color="bg1", required=True),
        PH("subtitle", "body", 1, g.m, mid + 1.45, g.cw, 1.0, size=s.subtitle, align="ctr", color="bg1"),
    ], background="tx2", hide_master=True, decor=[rule((g.w - RULE_W) / 2, mid + 1.25)]))
    gutter = two[1][0] - (two[0][0] + two[0][1])
    divider = Decor(two[0][0] + two[0][1] + gutter / 2 - 0.007, BODY_Y + 0.1, 0.014, single_h - 0.2, "tx1@20")
    add(LayoutDef("two-col", "Two Column", "Two lists side by side, such as before and after", [
        _title(g, s),
        PH("left", "body", 1, two[0][0], BODY_Y, two[0][1] - 0.2, single_h, size=s.two_col, bullets=True,
           anchor=single, lift=lift),
        PH("right", "body", 2, two[1][0] + 0.2, BODY_Y, two[1][1] - 0.2, single_h, size=s.two_col,
           bullets=True, anchor=single, lift=lift),
        _takeaway(g),
    ], decor=[divider]))
    if big_number == "dark":
        add(LayoutDef("big-number", "Big Number", "One number that makes the point, with a caption", [
            PH("number", "title", 0, g.m, 1.0, g.cw, 3.0, size=s.big_number, anchor="b", bold=True,
               color="accent2", required=True),
            PH("caption", "body", 1, g.m, 4.45, g.cw, 1.3, size=28, color="bg1", required=True),
        ], heading="number", background="tx2", hide_master=True, decor=[rule(g.m + 0.1, 4.2)]))
    else:
        add(LayoutDef("big-number", "Big Number", "One number that makes the point, with a caption", [
            PH("number", "title", 0, g.m, 1.0, g.cw, 3.0, size=s.big_number, anchor="b", bold=True, color="tx2",
               required=True),
            PH("caption", "body", 1, g.m, 4.45, g.cw, 1.3, size=28, required=True),
        ], heading="number", decor=[rule(g.m + 0.1, 4.2)]))
    add(LayoutDef("chart", "Chart", "A title and one native chart", [
        _title(g, s),
        PH("chart", "chart", 1, g.m, BODY_Y, g.cw, single_h, required=True),
        _takeaway(g),
    ]))
    add(LayoutDef("table", "Table", "A title and one table", [
        _title(g, s),
        PH("table", "tbl", 1, g.m, BODY_Y, g.cw, single_h, required=True),
        _takeaway(g),
    ]))
    add(LayoutDef("image", "Image", "A title, one image and a caption", [
        _title(g, s),
        PH("image", "pic", 1, g.m, BODY_Y, g.cw * 0.64, g.body_h, required=True),
        PH("caption", "body", 2, g.m + g.cw * 0.64 + 0.4, BODY_Y, g.cw * 0.36 - 0.4, g.body_h, size=caption),
    ]))
    add(LayoutDef("quote", "Quote", "A pull quote; the ## heading is the quote", [
        PH("quote", "body", 1, g.m + 0.8, 1.4, g.cw - 1.6, 3.6, size=32, anchor="ctr", italic=True,
           color="tx2", required=True),
        PH("attribution", "body", 2, g.m + 0.8, 5.35, g.cw - 1.6, 0.6, size=18),
    ], heading="quote", decor=[rule(g.m + 0.9, 5.15)]))
    add(LayoutDef("image-right", "Image Right", "Bullets on the left, an image on the right", [
        _title(g, s),
        PH("body", "body", 1, two[0][0], BODY_Y, two[0][1], single_h, size=s.two_col, bullets=True,
           anchor=single, lift=lift),
        PH("image", "pic", 2, two[1][0], BODY_Y, two[1][1], g.body_h, required=True),
    ]))
    icon_row = [_title(g, s)]
    icon, icon_y = 1.1, BODY_Y + 0.8
    for i, (x, w) in enumerate(three, start=1):
        icon_row.append(PH(f"icon{i}", "pic", 8 + 2 * i, x + (w - icon) / 2, icon_y, icon, icon,
                           required=i == 1))
        icon_row.append(PH(f"text{i}", "body", 9 + 2 * i, x + 0.15, icon_y + icon + 0.3, w - 0.3,
                           g.body_h - icon - 1.15, size=s.icon_text, align="ctr"))
    add(LayoutDef("icon-row", "Icon Row", "Three icons, each with a short line of text", icon_row))
    panel_h = g.body_h - 0.6
    panels = [Decor(x, BODY_Y, w, panel_h, "bg2") for x, w in two]
    add(LayoutDef("comparison", "Comparison", "Two labeled lists side by side, each on a tinted panel", [
        _title(g, s),
        PH("left-heading", "body", 1, two[0][0] + PANEL_PAD, BODY_Y + 0.25, two[0][1] - 2 * PANEL_PAD, 0.6,
           size=s.two_col + 2, bold=True, color="tx2"),
        PH("left", "body", 2, two[0][0] + PANEL_PAD, BODY_Y + 0.95, two[0][1] - 2 * PANEL_PAD,
           panel_h - 1.2, size=s.two_col, bullets=True),
        PH("right-heading", "body", 3, two[1][0] + PANEL_PAD, BODY_Y + 0.25, two[1][1] - 2 * PANEL_PAD, 0.6,
           size=s.two_col + 2, bold=True, color="tx2"),
        PH("right", "body", 4, two[1][0] + PANEL_PAD, BODY_Y + 0.95, two[1][1] - 2 * PANEL_PAD,
           panel_h - 1.2, size=s.two_col, bullets=True),
    ], decor=panels))
    add(LayoutDef("agenda", "Agenda", "The deck's sections, in order", [
        _title(g, s),
        PH("body", "body", 1, g.m, BODY_Y, g.cw, single_h, size=s.body + 4, bullets=True, numbered=True,
           anchor=single, lift=lift),
    ]))
    team = [_title(g, s)]
    for i, (x, w) in enumerate(four, start=1):
        side = min(w, 2.0)
        team.append(PH(f"photo{i}", "pic", 8 + 2 * i, x + (w - side) / 2, BODY_Y + 0.1, side, side))
        team.append(PH(f"name{i}", "body", 9 + 2 * i, x, BODY_Y + side + 0.25, w, 1.0, size=18, align="ctr"))
    add(LayoutDef("team", "Team", "Up to four people with photos and names", team))
    return d


SETS = {
    "minimal": ["title", "section", "content", "closing"],
    "standard": ["title", "section", "content", "two-col", "big-number", "chart", "table", "image", "quote",
                 "closing"],
    "full": ["title", "section", "agenda", "content", "two-col", "comparison", "big-number", "chart", "table",
             "image", "image-right", "icon-row", "team", "quote", "closing"],
}


def layout_set(name: str, width_in: float, height_in: float, scale: Scale | None = None,
               body_anchor: str = "middle", big_number: str = "light") -> list[LayoutDef]:
    defs = _defs(Grid(width_in, height_in), scale or Scale(), body_anchor, big_number)
    return [defs[k] for k in SETS[name]]
