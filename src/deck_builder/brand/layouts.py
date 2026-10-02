"""The layout sets `brand init` generates. Geometry is in inches on a margin grid, scaled to the slide size.

Placeholder idx values are part of the contract with tokens.yaml, so they never change for a layout key.
Type sizes come from a `Scale`, which `generate.type` in brand.yaml can override; a user can still restyle
the template in PowerPoint afterward, and `brand check` keeps the mapping honest.

Design rules the layouts follow (see `deck-builder docs design`): one title position on every content
slide; projected body text at 20 pt or more; sparse single-column content sits in the middle of the body
area instead of hugging the top; columns get structure (a tinted panel or a thin divider); one short
accent rule is the only decoration, used on title, section, closing and big-number slides. The designed
set adds structure drawn from shapes (cards, chevrons, bands, icon tiles), always in the primary color's
ramp, and nothing ornamental.
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
LOGO_SLOT_W, LOGO_SLOT_H = 1.8, 0.65  # the optional logo at a comparison panel's bottom right (designed set)
DEFAULT_INSET = 0.1  # inches: PowerPoint's left and right text inset when a box sets none
BULLET_HANG = 0.375  # inches: the master's first-level bullet indent, which every generated list keeps


@dataclass(frozen=True)
class Scale:
    """Type sizes in points. Defaults are sized for a projected 16:9 deck: nothing under 18 pt."""

    title: float = 32
    title_bold: bool = True
    subtitle: float = 24
    body: float = 24
    two_col: float = 20
    icon_text: float = 18
    table: float = 18
    big_number: float = 120
    kicker: float = 18  # the section label above a content-slide title (designed set)
    lede: float = 20  # the one-line subtitle under a content-slide title (designed set)

    @classmethod
    def from_meta(cls, gen: dict[str, Any]) -> Scale:
        """The mode's preset, then any sizes generate.type sets."""
        given = {**MODES[gen.get("mode", "projected")], **(gen.get("type") or {})}
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in given.items() if k in known})


# A projected deck is watched from across a room; a read deck is sent ahead and read on a screen, like
# the leave-behind decks consultancies hand over: smaller type, more on a slide, text from the top.
MODES: dict[str, dict[str, Any]] = {
    "projected": {},
    "read": {"title": 28, "subtitle": 18, "body": 14, "two_col": 13, "icon_text": 13, "table": 12,
             "big_number": 96, "kicker": 12, "lede": 15},
}
READ_MEASURE = 9.0  # inches: a read deck's single-column body, about 90 characters a line at 14 pt


@dataclass(frozen=True)
class Style:
    """The generate options that change shapes rather than sizes. The defaults are today's layouts."""

    takeaway: str = "band"  # band: a full-width band in the primary color | quote: an italic line, centered
    icon_tile: str = "none"  # none | square | circle: icon-row icons on a primary-color tile, drawn white
    band_label: str = "parallelogram"  # parallelogram | rectangle: the label shape on bands layouts
    process_icons: bool = False  # process steps hold a white icon, with the step's title under the arrow
    emphasis: str = "primary"  # primary | ink: the color of **bold** on cards and bands (designed set)
    ramp_floor: int = 60  # the lightest tint in the primary ramp; brand init computes it from the brand's colors

    @classmethod
    def from_meta(cls, gen: dict[str, Any]) -> Style:
        return cls(takeaway=str(gen.get("takeaway", "band")),
                   icon_tile=str((gen.get("icons") or {}).get("tile", "none")),
                   band_label=str((gen.get("bands") or {}).get("label_shape", "parallelogram")),
                   process_icons=bool((gen.get("process") or {}).get("icons", False)),
                   emphasis=str(gen.get("emphasis", "primary")))


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
    icon: bool = False  # a picture field that takes a brand icon, recolored (to color when it's set)
    emphasis: str | None = None  # a theme color for **bold** runs, written to tokens.yaml for the build
    fit: bool = False  # always fit the image inside the box (a logo slot), never crop it to fill
    fit_max: float | None = None  # a fitted image takes at most this share of the box, so a logo stays modest

    @property
    def text_h(self) -> float:
        """The height text can use: the box less the extra bottom inset that does the lift."""
        return self.h - 2 * self.lift

    @property
    def text_w(self) -> float:
        """The width text can use: the box less its side insets and, for a list, the bullet's hang."""
        side = self.inset if self.inset is not None else DEFAULT_INSET
        hang = (self.size or 18) * 1.6 / 72 if self.numbered else BULLET_HANG if self.bullets else 0.0
        return max(0.2, self.w - 2 * side - hang)


@dataclass
class Decor:
    """A drawn shape on a layout, behind its placeholders: a panel, a divider, the accent rule, a card,
    a process chevron, a band label or an icon tile.

    fill is a theme color (bg2, accent2 ...) or a tint written "tx2@70": tx2 lightened to 70% of its
    luminance range. geom is a DrawingML preset: rect, homePlate, chevron, parallelogram or ellipse.
    A fixed shape (an icon tile) keeps its size when the designed set moves a layout's body down.
    """

    x: float
    y: float
    w: float
    h: float
    fill: str
    geom: str = "rect"
    fixed: bool = False


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
    row: bool = False  # the build spaces the filled numbered slots (logo1, caption1 ...) evenly across the row


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


def _takeaway(g: Grid, style: str = "band") -> PH:
    """The optional so-what line: one sentence in a full-width band in the primary color, or (quote) an
    italic line in the primary color, centered under the content like a pull quote."""
    if style == "quote":
        return PH("takeaway", "body", 7, g.m, TAKEAWAY_Y, g.cw, TAKEAWAY_H, size=20, anchor="ctr", align="ctr",
                  italic=True, color="tx2")
    return PH("takeaway", "body", 7, g.m, TAKEAWAY_Y, g.cw, TAKEAWAY_H, size=18, anchor="ctr", bold=True,
              color="bg1", fill="tx2", inset=0.2)


def _defs(g: Grid, s: Scale, body_anchor: str, big_number: str, mode: str = "projected",
          designed: bool = False, style: Style | None = None) -> dict[str, LayoutDef]:
    st = style or Style()
    mid = g.h * 0.36
    two = g.cols(2)
    three = g.cols(3)
    four = g.cols(4)
    single = "ctr" if body_anchor == "middle" else "t"
    lift = OPTICAL_LIFT if body_anchor == "middle" else 0.0
    # Bodies end above the takeaway band, so short middle-anchored content centers at the optical
    # center, a little above the middle of the slide, rather than low in the body area.
    single_h = BODY_END - BODY_Y
    measure = min(g.cw, READ_MEASURE) if mode == "read" else g.cw  # line length for one column of text
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
    add(LayoutDef("content", "Content", "A title and a short bulleted list", [
        _title(g, s),
        PH("body", "body", 1, g.m, BODY_Y, measure, single_h, size=s.body, bullets=True, anchor=single, lift=lift),
        _takeaway(g, st.takeaway),
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
        _takeaway(g, st.takeaway),
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
        _takeaway(g, st.takeaway),
    ]))
    add(LayoutDef("table", "Table", "A title and one table", [
        _title(g, s),
        PH("table", "tbl", 1, g.m, BODY_Y, g.cw, single_h, required=True),
        _takeaway(g, st.takeaway),
    ]))
    add(LayoutDef("image", "Image", "A title, one image and a caption", [
        _title(g, s),
        PH("image", "pic", 1, g.m, BODY_Y, g.cw * 0.64, g.body_h, required=True, fit_max=LOGO_SHARE),
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
        PH("image", "pic", 2, two[1][0], BODY_Y, two[1][1], g.body_h, required=True, fit_max=LOGO_SHARE),
    ]))
    icon_row = [_title(g, s)]
    icon_decor: list[Decor] = []
    icon, icon_y = 1.1, BODY_Y + 0.8
    for i, (x, w) in enumerate(three, start=1):
        cx, cy = x + w / 2, icon_y + icon / 2
        if st.icon_tile in ("square", "circle"):  # a primary tile with the icon drawn white on it
            icon_decor.append(Decor(cx - TILE / 2, cy - TILE / 2, TILE, TILE, "tx2",
                                    "ellipse" if st.icon_tile == "circle" else "rect", fixed=True))
            icon_row.append(PH(f"icon{i}", "pic", 8 + 2 * i, cx - TILE_ICON / 2, cy - TILE_ICON / 2, TILE_ICON,
                               TILE_ICON, required=i == 1, icon=True, color="bg1"))
        else:
            icon_row.append(PH(f"icon{i}", "pic", 8 + 2 * i, cx - icon / 2, icon_y, icon, icon, required=i == 1,
                               icon=True))
        icon_row.append(PH(f"text{i}", "body", 9 + 2 * i, x + 0.15, icon_y + icon + 0.3, w - 0.3,
                           g.body_h - icon - 1.15, size=s.icon_text, align="ctr"))
    add(LayoutDef("icon-row", "Icon Row", "Three icons, each with a short line of text", icon_row,
                  decor=icon_decor))
    panel_h = g.body_h - 0.6
    panels = [Decor(x, BODY_Y, w, panel_h, "bg2") for x, w in two]
    logo_h = LOGO_SLOT_H if designed else 0.0  # the designed set gives each panel an optional logo slot
    comparison = [
        _title(g, s),
        PH("left-heading", "body", 1, two[0][0] + PANEL_PAD, BODY_Y + 0.25, two[0][1] - 2 * PANEL_PAD, 0.6,
           size=s.two_col + 2, bold=True, color="tx2"),
        PH("left", "body", 2, two[0][0] + PANEL_PAD, BODY_Y + 0.95, two[0][1] - 2 * PANEL_PAD,
           panel_h - 1.2 - logo_h, size=s.two_col, bullets=True),
        PH("right-heading", "body", 3, two[1][0] + PANEL_PAD, BODY_Y + 0.25, two[1][1] - 2 * PANEL_PAD, 0.6,
           size=s.two_col + 2, bold=True, color="tx2"),
        PH("right", "body", 4, two[1][0] + PANEL_PAD, BODY_Y + 0.95, two[1][1] - 2 * PANEL_PAD,
           panel_h - 1.2 - logo_h, size=s.two_col, bullets=True),
    ]
    if designed:  # bottom right of each panel, so headings keep their full width
        for n, edge in enumerate(("left", "right")):
            px, pw = two[n]
            comparison.append(PH(f"{edge}-logo", "pic", 5 + n, px + pw - PANEL_PAD - LOGO_SLOT_W,
                                 BODY_Y + panel_h - PANEL_PAD - logo_h + 0.1, LOGO_SLOT_W, logo_h - 0.1, fit=True))
    add(LayoutDef("comparison", "Comparison", "Two labeled lists side by side, each on a tinted panel",
                  comparison, decor=panels))
    add(LayoutDef("agenda", "Agenda", "The deck's sections, in order", [
        _title(g, s),
        PH("body", "body", 1, g.m, BODY_Y, measure, single_h, size=s.body + 4, bullets=True, numbered=True,
           anchor=single, lift=lift),
    ]))
    team = [_title(g, s)]
    for i, (x, w) in enumerate(four, start=1):
        side = min(w, 2.0)
        team.append(PH(f"photo{i}", "pic", 8 + 2 * i, x + (w - side) / 2, BODY_Y + 0.1, side, side))
        team.append(PH(f"name{i}", "body", 9 + 2 * i, x, BODY_Y + side + 0.25, w, 1.0, size=18, align="ctr"))
    add(LayoutDef("team", "Team", "Up to four people with photos and names", team))
    if designed:
        for n in CARDS:
            add(_cards(g, s, n, st))
        for n in STEPS:
            add(_process(g, s, n, st))
        for n in BANDS:
            add(_bands(g, s, n, st))
        add(_logos(g, s, st))
    return d


def ramp(n: int, floor: int = 60) -> list[str]:
    """n fills from the primary color (tx2) to a lighter tint of it, for cards, steps and band labels.
    floor is the lightest tint, which `brand init` sets from the brand's own colors (ramp_floor in
    generate.py) so white label text keeps its contrast on every step; at 100 every step is the primary."""
    if n == 1 or floor >= 100:
        return ["tx2"] * n
    return ["tx2" if i == 0 else f"tx2@{round(100 - (100 - floor) * i / (n - 1))}" for i in range(n)]


CARD_GAP, CARD_LABEL_H = 0.25, 0.62
CARDS, STEPS, BANDS = (2, 3, 4, 5), (3, 4, 5, 6), (2, 3, 4)  # the designed set's counts
TILE, TILE_ICON = 1.3, 0.75  # an icon tile and the white icon on it
STEP_ICON = 0.6  # a white icon inside a process chevron
LOGO_SHARE = 0.6  # a transparent image (a logo) takes at most this share of a large picture box
LOGO_SLOTS = 6
# Every card, step and band is required: its shape is drawn on the layout, so an empty one would show.


def _emphasis(st: Style) -> str | None:
    return "tx2" if st.emphasis == "primary" else None


def _cards(g: Grid, s: Scale, n: int, st: Style) -> LayoutDef:
    """n equal cards: a colored label band, bullets, and an optional bold footer line at the bottom."""
    phs, decor = [_title(g, s)], []
    top, bottom = BODY_Y, BODY_END
    text = s.icon_text
    for i, ((x, w), fill) in enumerate(zip(g.cols(n, CARD_GAP), ramp(n, st.ramp_floor), strict=True), start=1):
        decor.append(Decor(x, top, w, bottom - top, "bg2"))  # no rule above the footer: it's optional
        base = 30 + 10 * i
        phs.append(PH(f"label{i}", "body", base, x, top, w, CARD_LABEL_H, size=s.two_col, anchor="ctr",
                      align="ctr", bold=True, color="bg1", fill=fill, inset=0.12, required=True))
        phs.append(PH(f"body{i}", "body", base + 1, x + 0.2, top + CARD_LABEL_H + 0.2, w - 0.4,
                      bottom - top - CARD_LABEL_H - 1.25, size=text, bullets=True, required=True,
                      emphasis=_emphasis(st)))
        phs.append(PH(f"footer{i}", "body", base + 2, x + 0.2, bottom - 0.85, w - 0.4, 0.75, size=text,
                      bold=True, color="tx2", anchor="ctr"))
    phs.append(_takeaway(g, st.takeaway))
    return LayoutDef(f"cards-{n}", f"Cards {n}", f"{n} equal cards, each a colored label, bullets and a bold "
                     "footer line", phs, decor=decor)


def _process(g: Grid, s: Scale, n: int, st: Style) -> LayoutDef:
    """n process steps as arrow chevrons in a color ramp. Each chevron holds the step's short label, with
    its text below; or, with process icons on, a white icon, with the step's title and text below."""
    phs, decor = [_title(g, s)], []
    step_h, gap = 1.15, 0.1
    depth = step_h * 0.5  # the chevron's point and notch, at the preset's default adjustment
    # Each chevron's notch takes the previous one's point, so steps overlap by depth less the gap.
    w = (g.cw + (n - 1) * (depth - gap)) / n
    below = BODY_Y + step_h + 0.3
    for i, fill in enumerate(ramp(n, st.ramp_floor), start=1):
        x = g.m + (i - 1) * (w - depth + gap)
        decor.append(Decor(x, BODY_Y, w, step_h, fill, "homePlate" if i == 1 else "chevron"))
        base = 30 + 10 * i
        left = 0.15 if i == 1 else depth
        if st.process_icons:
            cx = x + (left + w - depth) / 2  # the middle of the chevron's body, between notch and point
            phs.append(PH(f"icon{i}", "pic", base + 2, cx - STEP_ICON / 2, BODY_Y + (step_h - STEP_ICON) / 2,
                          STEP_ICON, STEP_ICON, required=True, icon=True, color="bg1"))
            phs.append(PH(f"step{i}", "body", base, x + depth * 0.5, below, w - depth, 0.75, size=s.icon_text,
                          anchor="t", align="ctr", bold=True, color="tx2", required=True))
            phs.append(PH(f"text{i}", "body", base + 1, x + depth * 0.5, below + 0.8, w - depth,
                          BODY_END - below - 0.8, size=s.icon_text, align="ctr", required=True))
            continue
        phs.append(PH(f"step{i}", "body", base, x + left, BODY_Y, w - left - depth, step_h,
                      size=s.icon_text, anchor="ctr", align="ctr", bold=True, color="bg1", inset=0.04,
                      required=True))
        phs.append(PH(f"text{i}", "body", base + 1, x + depth * 0.5, below, w - depth,
                      BODY_END - below, size=s.icon_text, align="ctr", required=True))
    phs.append(_takeaway(g, st.takeaway))
    what = ("a white icon in an arrow, with a short title and a line of text under it" if st.process_icons
            else "a short label in an arrow with a line of text under it")
    return LayoutDef(f"process-{n}", f"Process {n}", f"{n} steps in order, each {what}", phs, decor=decor)


def _bands(g: Grid, s: Scale, n: int, st: Style) -> LayoutDef:
    """n labeled rows that fill the body: a colored label on the left, text on the right, thin rules between."""
    phs, decor = [_title(g, s)], []
    top, bottom = BODY_Y, g.h - FOOTER
    row = (bottom - top) / n
    label_w = min(3.2, g.cw * 0.27)
    text_x = g.m + label_w + 0.35
    slant = st.band_label != "rectangle"
    pad = 0.3 if slant else 0.15  # a parallelogram's slanted ends take room from the text
    for i, fill in enumerate(ramp(n, st.ramp_floor), start=1):
        y = top + (i - 1) * row
        decor.append(Decor(g.m, y + 0.14, label_w, row - 0.28, fill, "parallelogram" if slant else "rect"))
        if i > 1:
            decor.append(Decor(text_x, y, g.m + g.cw - text_x, 0.014, "tx1@20"))
        base = 30 + 10 * i
        phs.append(PH(f"label{i}", "body", base, g.m + pad, y + 0.14, label_w - 2 * pad, row - 0.28,
                      size=s.two_col, anchor="ctr", align="ctr", bold=True, color="bg1", required=True))
        phs.append(PH(f"text{i}", "body", base + 1, text_x, y + 0.08, g.m + g.cw - text_x, row - 0.16,
                      size=s.two_col, bullets=True, anchor="ctr", required=True, emphasis=_emphasis(st)))
    return LayoutDef(f"bands-{n}", f"Bands {n}", f"{n} labeled rows that fill the slide, a label on the left "
                     "and its points on the right", phs, decor=decor)


def _logos(g: Grid, s: Scale, st: Style) -> LayoutDef:
    """Up to six logos on one row, each with a caption under it. The build spaces the filled slots evenly
    across the row, so two logos sit as evenly as six; each logo fits inside its slot, never cropped."""
    phs = [_title(g, s)]
    slot_y, slot_h = BODY_Y + 0.9, 1.3
    for i, (x, w) in enumerate(g.cols(LOGO_SLOTS, 0.3), start=1):
        base = 30 + 10 * i
        clear = 0.15  # clear space around the logo, inside its slot
        phs.append(PH(f"logo{i}", "pic", base, x + clear, slot_y, w - 2 * clear, slot_h, required=i <= 2,
                      fit=True))
        phs.append(PH(f"caption{i}", "body", base + 1, x, slot_y + slot_h + 0.25, w, 1.0, size=s.icon_text,
                      align="ctr"))
    phs.append(_takeaway(g, st.takeaway))
    return LayoutDef("logos", "Logos", "Two to six logos on one row, each with a caption, such as the tools a "
                     "slide is about", phs, row=True)


KICKER_Y, KICKER_H = 0.28, 0.42  # room for an 18 pt label, the projected floor
HEADED_TITLE_Y, HEADED_TITLE_H = 0.68, 0.8
LEDE_Y, LEDE_H = 1.5, 0.48
HEADED_BODY_Y = 2.05


def with_headers(ld: LayoutDef, g: Grid, s: Scale) -> LayoutDef:
    """A content-family layout with a section label above the title and a one-line subtitle under it.

    Everything below the title moves down and keeps its bottom edge: a y in [BODY_Y, bottom] maps
    linearly onto [HEADED_BODY_Y, bottom]. Pictures keep their size and only move, so icons stay square;
    icons and fixed shapes (icon tiles) move by their centers, so an icon stays centered on its tile or
    chevron.
    """
    if not any(ph.field == "title" and ph.y == TITLE_Y for ph in ld.phs):
        return ld  # title, section, closing, big-number and quote slides have no content header
    bottom = g.h - FOOTER
    k = (bottom - HEADED_BODY_Y) / (bottom - BODY_Y)

    def move(y: float) -> float:
        return HEADED_BODY_Y + (y - BODY_Y) * k if y >= BODY_Y - 1e-6 else y

    phs: list[PH] = []
    for ph in ld.phs:
        if ph.field == "title":
            phs.append(PH(**{**ph.__dict__, "y": HEADED_TITLE_Y, "h": HEADED_TITLE_H}))
        elif ph.icon:
            phs.append(PH(**{**ph.__dict__, "y": move(ph.y + ph.h / 2) - ph.h / 2}))
        else:
            y2 = move(ph.y + ph.h) if ph.kind != "pic" else min(move(ph.y) + ph.h, bottom)
            phs.append(PH(**{**ph.__dict__, "y": move(ph.y), "h": max(0.3, y2 - move(ph.y)),
                             "lift": ph.lift * k}))
    # idx 18 and 19: free on every layout, and below the footer and slide number's 20 and 21
    phs.insert(1, PH("kicker", "body", 18, g.m, KICKER_Y, g.cw, KICKER_H, size=s.kicker, bold=True,
                     color="tx2", anchor="b"))
    phs.insert(2, PH("subtitle", "body", 19, g.m, LEDE_Y, g.cw, LEDE_H, size=s.lede, anchor="t"))
    decor = []
    for d in ld.decor:
        if d.fixed:
            y, h = move(d.y + d.h / 2) - d.h / 2, d.h
        else:
            y, h = move(d.y), max(0.014, move(d.y + d.h) - move(d.y)) if d.h > 0.02 else d.h
        decor.append(Decor(d.x, y, d.w, h, d.fill, d.geom, d.fixed))
    return LayoutDef(ld.key, ld.name, ld.description, phs, ld.heading, ld.background, ld.hide_master, decor,
                     ld.row)


SETS = {
    "minimal": ["title", "section", "content", "closing"],
    "standard": ["title", "section", "content", "two-col", "big-number", "chart", "table", "image", "quote",
                 "closing"],
    "full": ["title", "section", "agenda", "content", "two-col", "comparison", "big-number", "chart", "table",
             "image", "image-right", "icon-row", "team", "quote", "closing"],
}
# The designed set: the full set, every content slide with a section label and a subtitle line, plus
# cards, process, band and logo-row layouts built from shapes rather than loose text.
SETS["designed"] = (SETS["full"][:-1] + [f"cards-{n}" for n in CARDS] + [f"process-{n}" for n in STEPS]
                    + [f"bands-{n}" for n in BANDS] + ["logos", "closing"])


def layout_set(name: str, width_in: float, height_in: float, scale: Scale | None = None,
               body_anchor: str = "middle", big_number: str = "light", mode: str = "projected",
               style: Style | None = None) -> list[LayoutDef]:
    g, s = Grid(width_in, height_in), scale or Scale()
    designed = name == "designed"
    defs = _defs(g, s, body_anchor, big_number, mode, designed, style)
    out = [defs[k] for k in SETS[name]]
    return [with_headers(ld, g, s) for ld in out] if designed else out
