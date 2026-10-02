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

palette:                         # named colors, 6-digit hex; name them by role, not hue
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
  layout_set: standard           # minimal | standard | full
  logo_on_master: primary        # a logo id, or leave out
  slide_numbers: true            # a small number at the bottom left of content slides (default true)
  body_anchor: middle            # middle | top: where single-column body text sits (default middle)
  big_number: light              # light | dark: dark puts the numeral on the primary color (default light)
  type:                          # type sizes in points; leave any key out to keep its default
    title: 32                    # content-slide titles
    title_bold: true
    subtitle: 24                 # title and closing slides
    body: 24                     # single-column body; the agenda is 4 pt larger
    two_col: 20                  # two-column, comparison and image-right text
    icon_text: 18
    table: 16                    # table text, header included
    big_number: 120
```

The defaults are sized for a projected 16:9 deck. For a leave-behind document read on screen, smaller
sizes fit more: for example `body: 18`, `two_col: 16`, `table: 12`. Character budgets in `tokens.yaml`
are computed from these sizes, so changing them changes how much text each field takes.

Since `--force` regenerates from `brand.yaml` alone, put type and placement choices in `generate:` rather
than in the template, so they survive a regenerate.

`deck-builder docs design` describes the design rules the generated layouts follow.

## Layout sets

| Set | Layouts |
|---|---|
| minimal | title, section, content, closing |
| standard | minimal plus two-col, big-number, chart, table, image, quote |
| full | standard plus agenda, comparison, image-right, icon-row, team |

## Fonts

Every machine that renders needs the fonts installed, or the renderer substitutes and `render`
reports `MISSING_FONT`. If decks go to people without the fonts, choose fonts that ship with
Office, or embed them in PowerPoint (File > Options > Save > Embed fonts) where the font license
allows it.
