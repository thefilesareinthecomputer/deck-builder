# brand.yaml: the brand's standards

What a person decides about the brand. `deck-builder brand init <slug> --from brand.yaml` generates the
template and `tokens.yaml` from it; `deck-builder schema brand` prints the full schema.

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
```

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
