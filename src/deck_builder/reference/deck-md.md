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
---

## Paper volume grew 12% in Q3         <- one heading = one slide
layout: content                        <- leading key: value lines are fields
subtitle: optional inline field

- Body bullets go to the `body` field  <- free content after the fields
  - Indent two spaces per level
- **Bold**, *italic*, `code` and [links](https://example.com) are the inline markup

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

## Value kinds

| Kind | Write it as |
|---|---|
| text | One paragraph, or a `key: value` field |
| bullets | `- item` lines; numbered lines also work |
| image | `![alt text](assets/photo.png)`, or `![alt](brand:logo/primary)`, on its own line in the field's `### name` section (or the body); files inside the deck's folder only. A `key:` line takes only a bare path such as `left-logo: assets/logo.png`, with no alt text |
| icon | `brand:icon/<id>` as the field value |
| table | A pipe table, or a ```` ```table ```` block with `header:` and `rows:` |
| chart | A ```` ```chart ```` block, below |

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

## Bulk mode

`{{column}}` anywhere in the file is replaced from a data row:
`deck-builder build template.md --data rows.csv --name "{{client}}.pptx"` builds one deck per row.
Data values are one line of plain text: a line break, or a value that would start a heading or image
line, is `BAD_DATA_VALUE` for that row.
