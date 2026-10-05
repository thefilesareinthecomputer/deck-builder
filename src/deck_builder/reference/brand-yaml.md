# brand.yaml: the brand's standards

What a person decides about the brand. `deck-builder brand init <slug> --from brand.yaml` generates the
template and `tokens.yaml` from it. `--force` regenerates both again from `brand.yaml`, replacing
any change made outside it, including tuned budgets and edits made in PowerPoint.
`deck-builder schema brand` prints the full schema.

```yaml
spec_version: 1
name: Pemberton Paper Co.        # display name
slug: pemberton                  # folder name; decks say `brand: pemberton`
version: 1.0.0                   # bump on any change that affects output
description: Sales and ops decks

palette:                         # named colors, 6-digit hex; keys in lowercase with hyphens, by role, not hue
  primary: "1F3A5F"
  accent: "E07A2F"
  ink: "1B1B1B"                  # body text
  muted: "6B7280"
  surface: "F4F5F7"              # light fills, table bands
  background: "FFFFFF"

theme_colors:                    # PowerPoint theme slots -> palette names or hex
  dk1: ink                       # text on light backgrounds
  lt1: background                # light background, text on dark backgrounds
  dk2: primary                   # titles, dark slide backgrounds
  lt2: surface
  accent1: primary               # chart series 1, and so on
  accent2: accent
  accent3: muted
  accent4: "9DB4C0"
  accent5: "C8553D"
  accent6: "5B8C5A"
  hlink: accent
  folHlink: muted

fonts:                           # set in the theme, so every placeholder inherits them
  heading: {family: Inter, fallback: Arial}
  body: {family: Inter, fallback: Arial}
  code: {family: Menlo, fallback: Consolas}   # code blocks and `code`; default Menlo. Code runs are marked
                                              # fixed-pitch, so a machine without it substitutes a monospace font

logos:                           # id -> PNG under this folder; decks use brand:logo/<id>
  primary: assets/logo.png
  mono: assets/logo-mono.png

icons:
  dir: assets/icons              # PNG alpha masks, one per icon; file name = id (brand:icon/<id>)
  default_color: accent          # recolored at build time; a layout field can set its own color
  source: "Where the icons came from and their license"

voice:                           # writing rules the agent follows; not enforced
  - One idea per slide. The title states the takeaway.

lint:                            # enforced by `check`
  max_slides: 40
  banned_patterns: ["—", "(?i)\\bsynerg"]   # Python regex over slide text and notes

generate:                        # read only by `brand init`
  slide_size: "16:9"             # 16:9 | 4:3
  layout_set: standard           # minimal | standard | full | designed
  logo_on_master: primary        # a logo id, or leave out
  slide_numbers: true            # a small number at the bottom left of content slides (default true)
  mode: projected                # projected | read: presented to a room, or sent and read on screen
  body_anchor: middle            # middle | top: where single-column body text sits (read mode: top)
  big_number: light              # light | dark: dark puts the numeral on the primary color (default light)
  takeaway: band                 # band | quote: a band in the primary color, or an italic line under the content
  icons: {tile: none}            # none | square | circle: icon-row icons drawn white on a primary-color tile
  bands: {label_shape: parallelogram}  # parallelogram | rectangle (designed set)
  process: {icons: false}        # true: each process step holds a white icon, its title under the arrow (designed set)
  emphasis: primary              # primary | ink: the color of **bold** on cards and bands (designed set)
  code: {theme: light}           # light | dark: code on the surface color, or light code on the ink color
                                 # (full and designed sets)
  type:                          # type sizes in points; leave any key out to keep the mode's size
    title: 32                    # content-slide titles (read: 28)
    title_bold: true
    subtitle: 24                 # title and closing slides (read: 18)
    body: 24                     # single-column body; the agenda is 4 pt larger (read: 14)
    two_col: 20                  # two-column, comparison and image-right text (read: 13)
    icon_text: 18                # (read: 13)
    table: 18                    # table text, header included (read: 12)
    big_number: 120              # (read: 96)
    kicker: 18                   # designed set: the section label above a content title (read: 12)
    lede: 20                     # designed set: the subtitle line under a content title (read: 15)
    code: 18                     # full and designed sets: code blocks (read: 12)
    statement: 40                # full and designed sets: the statement slide's sentence (read: 28)
```

Title color is the `dk2` theme slot, which also fills the dark slide backgrounds (title, section,
closing), so a bright title color makes those slides bright too. Content-slide title size is
`generate.type.title`; `brand check` warns `TYPE_LARGE` with the size that fits when it's too big for
the box. The title and section slides' own title sizes come from the layout set and have no setting.

Pick the mode by how the deck is used. A projected deck keeps every size at 18 pt or more. A read deck
sets single-column text to a 9 in measure so lines stay readable at its smaller size. Character budgets
in `tokens.yaml` are computed from these sizes, so changing them changes how much text each field takes.

Since `--force` regenerates from `brand.yaml` alone, put type and placement choices in `generate:` rather
than in the template, so they survive a regenerate.

A generated kit holds its own recipe and ingredients: `brand.yaml` and the logos and icons it names are
copied into the kit. `deck-builder brand init <slug> --force`, with no `--from`, regenerates the kit
from them, after copying the kit as it was into its `backups/` folder. `brand check` warns `KIT_STALE`
when the palette, fonts, `generate` settings or the master logo changed since the kit was generated,
or when another version generated it.

`deck-builder docs design` describes the design rules the generated layouts follow.

## Layout sets

| Set | Layouts |
|---|---|
| minimal | title, section, content, closing |
| standard | minimal plus two-col, big-number, chart, table, image, quote |
| full | standard plus agenda, comparison, image-right, icon-row, team |
| designed | full plus cards-2 to cards-5, process-3 to process-6, bands-2 to bands-4 and logos; every content slide also takes `kicker:` and `subtitle:`, and comparison takes `left-logo:` and `right-logo:` |

The designed set's extra layouts are built from shapes rather than loose text. Cards are equal
columns, each with a colored label band, bullets and a bold footer line. Process steps are chevrons
in a ramp of the primary color, each with a short label inside and a line of text below. Bands are
labeled rows that fill the slide, a label on the left and its points on the right. Every card, step
and band must be filled, since its shape is drawn whether or not it has text: pick `cards-3` for
three items and `cards-4` for four. A card's footer line is optional. The ramp of the primary color
on cards, steps and bands lightens only as far as white labels keep 4.5:1 contrast, worked out from
the brand's own colors. `logos` places two to six logos with captions on one row; the build spaces
the filled slots evenly and fits each logo inside its slot, never cropped. `kicker:` is a
short section label above the title, and `subtitle:` is one line under it; leave either out and
nothing is drawn, though the title and body keep their designed-set positions.

## Fonts

Every machine that renders needs the fonts installed, or the renderer substitutes and `render`
reports `MISSING_FONT`. If decks go to people without the fonts, choose fonts that ship with
Office, or embed them in PowerPoint (File > Options > Save > Embed fonts) where the font license
allows it.
