# The deck.xlsx format

A workbook holds the same deck as a `deck.md`, and `deck-builder convert` turns either into the
other without losing anything. `convert deck.md deck.xlsx` writes a workbook set up for a team:
a layout dropdown, a frozen header row, live character counts against each field's budget, and a
README sheet.

## Sheets

| Sheet | Holds |
|---|---|
| `slides` | One row per slide: `slide`, `layout`, `title`, one column per field, `notes` |
| `deck` | `key` and `value` columns: the front matter, values written as YAML (`'12'` is the text 12) |
| `chart-NN-<field>` | One chart: option rows, a blank row, then categories down column A and one series per column |
| `table-NN-<field>` | One table: a header row, then data rows |
| `README` | Instructions; ignored by the engine |
| `_lists` | Hidden; feeds the dropdown and the counts |

## Cells on the slides sheet

| Value | Write it as |
|---|---|
| Text | Plain text; `**bold**`, `*italic*`, `` `code` `` and `[text](url)` work as in deck.md |
| Bullets | One per line, starting `- `; two spaces of indent per level |
| Image | `![alt text](assets/photo.png)` or `![alt](brand:logo/primary)` |
| Icon | `brand:icon/<id>` |
| Code | The whole fenced block, fences and language included, as in deck.md (`.csv` can't hold it) |
| Chart or table | `sheet:<sheet name>` |
| `current` column | The item or card a map slide marks, as in deck.md's `current:` |
| `build` column | The field (or `slots`) that fades in one click at a time, as in deck.md's `build:` |

Columns whose header starts with `#` are helpers and ignored. The engine reads cell values only, so
re-saving in Excel, SharePoint or LibreOffice changes nothing.

## Chart sheet

```
type           | column
number_format  | #,##0
labels         | true
legend         |            (blank: on for pie charts and for two or more series)
title          |
colors         | primary, accent
               |
category       | Copy paper | Card stock
Jul            | 9800       | 3100
Aug            | 10400      | 3050
```

CSV holds the `slides` sheet alone, so it has no place for front matter, charts or tables;
`convert` refuses with `CONVERT_LOSSY` rather than drop them.
