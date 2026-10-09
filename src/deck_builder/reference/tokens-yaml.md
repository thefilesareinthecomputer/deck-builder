# tokens.yaml: the template contract

Maps the brand's logical layouts and fields onto the template's layouts and placeholders, and holds
the content budgets `check` enforces. `brand init` and `brand adopt` write it; people tune the
budgets after a test render. `deck-builder schema tokens` prints the full schema.

```yaml
spec_version: 1
text:
  code_font: Menlo               # code blocks and `code` in slide text; brand.yaml fonts.code sets it
code:                            # code blocks; brand init writes it from the palette
  theme: light                   # light: the surface color | dark: the ink color
  panel: surface                 # the panel behind the code
  highlight: "E1E5EA"            # the band behind highlighted lines
  colors:                        # one per token role, each at 4.5:1 on the panel and the band
    keyword: primary             # bold
    type: primary
    function: primary
    string: "B05A1C"             # brand init darkens (or, dark, lightens) a color under 4.5:1
    number: "B05A1C"
    comment: muted               # italic; also the line numbers and the filename
    operator: ink
    plain: ink
chart:                           # styling for charts the engine draws; colors are palette names or hex
  font_size: 12
  text_color: ink                # data labels
  axis_text_color: muted         # axis labels, the baseline and the legend: muted, or ink when muted is
                                 # under 4.5:1 on the background
  gridline_color: "E8E8E8"       # hairline gridlines, a faint tint of ink
  colors: [primary, accent, muted]
table:                           # brand init writes every key, so each is visible and tunable
  font_size: 16                  # body cells; from brand.yaml generate.type.table
  header_font_size: 16
  row_height_factor: 2.0         # row height as a multiple of the font size
  header_fill: primary
  header_text: background
  row_fill: background
  text: ink
  rule: "D1D4D3"                 # a thin rule between body rows, and no vertical lines; leave out for none
  # band_fill: surface           # optional: fill every other body row instead of, or as well as, rules
  status: {Green: "15803D", Amber: "B45309", Red: "B91C1C"}  # exact cell value -> dot color, case-insensitive
generated:                       # written by brand init; a record, not a setting
  by: deck-builder 0.1.0         # the engine that generated the kit
  inputs_sha256: "..."           # palette, theme colors, fonts, generate settings and master logo
                                 # brand check warns KIT_STALE when these no longer match
furniture:                       # written by brand init; a record, not a setting
  slide_numbers: true            # from brand.yaml generate.slide_numbers
  color: muted                   # numbers and footers: muted, or ink when muted is under 4.5:1
layouts:
  content:                       # the name decks use: `layout: content`
    template_layout: Content     # the layout's name in the template
    master: null                 # only when several masters reuse a layout name
    heading_field: title         # the field the ## heading fills (default: title)
    description: A title and up to six bullets
    fields:
      title: {idx: 0, kind: text, max_chars: 70, required: true}
      body:  {idx: 1, kind: bullets, max_chars: 420, max_bullets: 6, max_bullet_chars: 110, max_level: 1}
```

## Fields

| Key | Meaning |
|---|---|
| `idx` | The placeholder's index on the template layout; `deck-builder inspect <template>` lists them |
| `kind` | `text`, `bullets`, `table`, `chart`, `image`, `icon` or `code` |
| `required` | `check` fails when the field is empty |
| `max_chars` | Characters after inline markup is removed |
| `max_bullets`, `max_bullet_chars`, `max_level` | Bullet count, per-bullet length, deepest nesting (0 = flat) |
| `line_chars`, `max_lines` | Characters a line holds and lines the box holds; `check` wraps the text word by word at `line_chars`, adds the space before each bullet, and reports `BUDGET_LINES` past `max_lines`. `brand init` writes both; an adopted kit can leave them out |
| `emphasis` | A color for `**bold**` runs in the field |
| `fit`, `fit_max` | Image fields: always fit inside the box, never crop; a fitted image takes at most this share of the box |
| `max_rows`, `max_cols` | Table limits, header row not counted in rows; `brand init` sets rows to what fits the placeholder at one line per row |
| `max_cols`, `max_lines` on a `code` field | Characters a line of code holds and lines the panel holds, exact for a monospace font; `check` reports `CODE_LONG` past either |
| `color` | Icon fields: the palette name or hex the icon is recolored to |

## Tuning budgets

Build a deck that fills each layout's text fields to their budgets, render it, and look at what
overflowed.
`render` reports `OVERFLOW_MEASURED` per field with the overrun. Lower `max_chars` until nothing
overflows, then leave about 10% headroom. After editing the template in PowerPoint, run
`deck-builder brand check <slug>`; a moved placeholder shows as `TEMPLATE_MISMATCH`.
