# The deck.md format

````markdown
---
spec_version: 1
brand: neutral                 # a slug from `deck-builder brand list`
title: Quarterly review        # written to the file's properties
author: Sales Ops
date: 2026-01-15               # created and modified dates; default 2000-01-01
default_layout: content        # used when a slide has no layout:
slide_level: 2                 # heading level that starts a slide (default 2)
output: ../../out/quarterly-review.pptx   # relative to this file; a .pptx in its folder or in out/
footer: Confidential           # optional small text after the slide number; no footer without it
slide_numbers: false           # optional; slide numbers are on by default where the brand has them
first_slide_number: 21         # optional; an excerpt of a larger deck numbers its slides from here
kicker: Q3 review              # optional; the section label on every slide whose layout has one and
                               # that sets none itself (kicker: "" on a slide leaves it blank)
fit: contain                   # optional; every image shown whole unless its slide sets fit: (a deck of
                               # screenshots)
---

## Paper volume grew 12% in Q3         <- one heading = one slide
layout: content                        <- leading key: value lines are fields
subtitle: optional inline field

- Body bullets go to the `body` field  <- free content after the fields
  - Indent two spaces per level
- **Bold**, *italic*, ***both***, `code` and [links](https://example.com) are the inline markup

### right                              <- a named field section
- Content for the `right` field

Notes:                                 <- speaker notes to the end of the slide
Source: the Q3 shipment ledger.
````

## How content maps to fields

- The `##` heading fills the layout's `heading_field` (default `title`).
- `key: value` lines right after the heading are fields. Values are YAML, so quote anything with `: `.
  Write `caption: "Goal: 12% growth"`, not `caption: Goal: 12% growth`.
- Content after the fields is the `body` section. If the layout has no `body` field, it goes to
  the layout's only unfilled field of the matching kind.
- `### name` starts the section for field `name`. Any other heading line inside a slide, such as
  `### Two words` or `# Note`, is a PARSE error.
- A section holds text or one visual, not both. Give a caption its own field.
- `current: n` under the heading marks item n of the slide's list (an agenda) or card n of a `cards-N`
  slide: everything else is muted, for a map slide that a deck in parts returns to.
- `build: <field>` makes that field fade in when presenting: a list one item per click, anything else
  (a chart, an image, a text field) as a whole. `build: slots` brings in a cards, process or bands slide
  one card, step or band per click. The effect is a half-second fade and nothing else; there are no
  transitions between slides. The PDF and renders show the finished slide.
- `fit: contain` shows the slide's images whole: scaled to fit their boxes, with their own ratio and
  edges, never cropped or stretched. `fit: cover` fills the boxes, cropping what's over. Without it on
  the slide, the front matter's `fit:` applies; without either, an image in a `screenshots/` folder or
  named by an image cue (below) is contained, and any other image covers its box.

## Images in the notes

A line in the speaker notes that starts with `SCREENSHOT:` or `DIAGRAM:` is an image cue: an image the
slide is meant to show. Its path comes first, relative to the deck file, then anything else after `|`.
Keep screenshots in the deck folder's `assets/screenshots/`, and give the slide's image field the same
path as its cue:

```markdown
## Runs finish in four minutes
layout: image-right

- The scheduler starts each run at six

### image
![The run page after a full run](assets/screenshots/run-page.png)

Notes:
SCREENSHOT: assets/screenshots/run-page.png | shows: the run page after a full run
```

`check` warns `IMAGE_NO_SLOT` when the cues name more images than the slide's layout holds, and lists
the layouts that hold them with what moving the slide costs. Only `image`, `image-right`, `image-2` and
`image-full` hold a photo or screenshot. `deck-builder assets --images <deck>` lists every image the deck
names and where it lands: shown, cropped, notes only, missing or unused.

## Value kinds

| Kind | Write it as |
|---|---|
| text | One paragraph, or a `key: value` field |
| bullets | `- item` lines; numbered lines also work |
| image | `![alt text](assets/photo.png)`, or `![alt](brand:logo/primary)`, on its own line in the field's `### name` section (or the body); files inside the deck's folder only. A `key:` line takes only a bare path such as `left-logo: assets/logo.png`, with no alt text. `image-2` takes `### image1` and `### image2` |
| icon | `brand:icon/<id>` as the field value; an id the kit lacks comes from the engine's starter icons (`brand show` lists both) |
| table | A pipe table, or a ```` ```table ```` block with `header:` and `rows:` |
| chart | A ```` ```chart ```` block, below |
| code | A fenced block with its language, such as ```` ```python ````, below |

A body cell whose trimmed value matches a `table.status` key in tokens.yaml, case-insensitively, gets
a colored dot before its text; the word itself still prints, so the color is never the only signal.

````markdown
```chart
type: column          # column | stacked-column | bar | stacked-bar | line | pie | doughnut
number_format: '#,##0'
labels: true
legend: true          # default: on for pie and for two or more series
title: optional chart title
colors: [primary, accent]   # palette names or hex; default from the brand
categories: [Jul, Aug, Sep]
series:
  - name: Copy paper
    values: [41200, 37800, 33100]
```
````

Charts are native PowerPoint charts with their data embedded, so they stay editable.

## Code blocks

A fenced block with a language tag is code: ```` ```python ````, ```` ```sql ````, ```` ```yaml ````,
```` ```bash ```` or any language Pygments knows (`text`, or no tag, is plain). It goes in the `code` field of
the `code` and `code-right` layouts, as the free body or in a `### code` section. It builds as editable text in
the brand's code font, one color per kind of token, keywords bold and comments italic, on a panel that fits it.

`````markdown
```python {4-5} lines title="forecast.py"
def weekly_forecast(orders, weeks=12):
    ...
```
`````

- `{4-5}` highlights lines (`{3,5-7}` for several); `lines` adds line numbers; `title="forecast.py"` adds a
  filename line, which takes two lines of the panel.
- Code never wraps. `check` reports `CODE_LONG` for a line wider than the panel (line numbers take their
  width from it) or more lines than it holds, and `CODE_LANGUAGE` for a tag the highlighter doesn't know.
  `brand show` lists each code field's characters and lines.
- Fences follow CommonMark: ```` ``` ```` or `~~~`, closed by the same character at least as many times. A
  four-backtick block holds a markdown example with its own three-backtick fence.
- Tabs become four spaces; trailing spaces and blank first and last lines are dropped.
- `chart` and `table` blocks keep their meaning above.

## Bulk mode

`{{column}}` anywhere in the file is replaced from a data row:
`deck-builder build template.md --data rows.csv --name "{{client}}.pptx"` builds one deck per row.
Data values are one line of plain text: a line break, or a value that would start a heading or image
line, is `BAD_DATA_VALUE` for that row.
