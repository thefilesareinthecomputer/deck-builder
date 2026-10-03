# Issue codes

Generated from the engine by `deck-builder docs codes`. Fix by code, not by message text.

| Code | Cause | Fix |
|---|---|---|
| `AMBIGUOUS_DECK` | A folder passed as the deck holds more than one of deck.md, deck.xlsx and deck.csv. | Pass the deck file itself, or remove the extra copy from the folder. |
| `PARSE` | The input can't be parsed: bad YAML, an unclosed block, a malformed table, or no slides. | Fix the syntax at the reported line; `deck-builder docs deck-md` shows the format. |
| `SPEC_VERSION` | The input declares a spec_version newer than this engine supports. | Upgrade deck-builder, or lower spec_version if the input doesn't use newer features. |
| `SCHEMA` | brand.yaml, tokens.yaml or a manifest doesn't match its JSON Schema. | Fix the listed keys; `deck-builder schema brand` or `deck-builder schema tokens` prints the schema. |
| `UNKNOWN_BRAND` | The deck names a brand slug that no brand_paths entry contains. | Run `deck-builder brand list` and use a listed slug, or add the kit's folder to brand_paths. |
| `BRAND_DUPLICATE` | Two brand kits under brand_paths use the same slug. | Rename one kit's slug in its brand.yaml and folder, or remove one path from brand_paths. |
| `BRAND_INVALID` | A brand kit is missing a required file or fails `brand check`. | Run `deck-builder brand check <slug>` and fix what it lists. |
| `TEMPLATE_MISMATCH` | tokens.yaml names a template layout or placeholder idx the template doesn't have. | Run `deck-builder inspect <template>` and correct template_layout or idx in tokens.yaml. |
| `UNKNOWN_LAYOUT` | A slide uses a layout name the brand doesn't define. | Use a layout from `deck-builder brand show <slug>`. |
| `UNKNOWN_FIELD` | A slide sets a field its layout doesn't have. | Use the layout's field names from `brand show`, or switch to a layout that has the field. |
| `MISSING_FIELD` | A required field for the slide's layout is empty. | Fill the field, or choose a layout where it isn't required. |
| `KIND_MISMATCH` | A field got the wrong kind of value, such as a table in a text field. | Give the field the kind `brand show` lists, or move the content to a field of that kind. |
| `BUDGET_CHARS` | A field has more characters than its budget. | Cut words, split the slide, or move detail to speaker notes. Never raise the budget to pass. |
| `BUDGET_BULLETS` | A bullets field has more bullets than its budget. | Merge or cut bullets, or split the slide. |
| `BUDGET_BULLET_CHARS` | A single bullet is longer than the per-bullet budget. | Shorten the bullet or split it into two. |
| `BUDGET_LEVEL` | Bullets nest deeper than the field allows. | Flatten the nesting. |
| `TABLE_SHAPE` | A table has no header, too many rows or columns, or rows of different lengths. | Fix the table so every row matches the header and fits the field's limits. |
| `TABLE_TALL` | A table's estimated rendered height, from its row count and each row's wrapped line count, exceeds its layout placeholder's height. | Shorten cell text, cut rows or columns, or choose a layout with a taller table placeholder. |
| `CHART_SHAPE` | A chart has an unknown type, no categories or series, or a series of the wrong length. | Give every series one value per category and use a supported chart type. |
| `UNKNOWN_ASSET` | A brand:logo, brand:icon or palette name doesn't exist in the brand. | Run `deck-builder assets <slug>` for the available ids. |
| `ASSET_FORMAT` | An image is in a format PowerPoint placeholders can't take, such as SVG. | Convert it to PNG or JPEG. |
| `ASSET_LOW_RES` | An image is smaller than its placeholder at 150 DPI and will look soft. | Use a larger source image. |
| `BUDGET_LINES` | A text field, wrapped at its box's line length, needs more lines than the box holds. A list counts each bullet's own lines and the space before it, so short lines that make every bullet wrap show here even under the character budget. | Shorten the bullets that wrap so each fits on one line, use fewer bullets, or move detail to the notes. |
| `CODE_LONG` | A code block has a line longer than its panel is wide, or more lines than the panel holds (a `title=` filename line takes two). Code never wraps, so the line would run off the panel. As a warning: an inline `code` span longer than a line of its text field, which breaks mid-token. | Break the long line where the language allows, shorten names, cut lines that don't make the point, or split the code across two slides. Keep an inline span short, or move it to a code block. |
| `CODE_LANGUAGE` | A code block's language tag isn't one the highlighter knows, so the block builds as plain text. | Use the language's usual name or short alias (python, sql, yaml, bash, json, ts); `text` is plain on purpose. |
| `CODE_LINES_MANY` | A code block on a projected slide has more than 12 lines, more than an audience reads during one slide. A convention from `docs design`, so it warns. | Cut to the lines that make the point and mark them with `{3,5-7}`, or move the full listing to the notes or an appendix. |
| `PROSE_TELL` | Slide text has a countable writing tell: a dash, curly quote, ellipsis or arrow character, an emoji, an inflated word (leverage, seamless, robust), an intensifier standing in for a number (significantly, dramatically), a filler transition (moreover, that said), a teaser (here's the catch), or a third "X, not Y" contrast in the deck. Speaker notes, code and quoted words are left alone. | Use the plain word or the number, cut the filler, state the point instead of teasing it, and type the plain character. `docs design` has the writing rules. |
| `BULLETS_MANY` | A list on a projected slide has more than four bullets, past what an audience holds at once. A convention from `docs design`, so it warns. | Cut to the four that make the point, split the slide, or move detail to the speaker notes. |
| `WORDS_MANY` | A projected slide has more than 60 words; about 40 reads well from the back of a room. A convention from `docs design`, so it warns. | Move detail to the speaker notes, or split the slide. |
| `LAYOUT_RUN` | More than three slides in a row use the same layout, so the deck reads as a document. A convention from `docs design`, so it warns. | Match each point to the layout that shows it (`docs design` has the table): a number as big-number, parallel options as cards or comparison, steps as process. |
| `SERIES_MANY` | A chart has more than eight series, more than its colors keep apart. | Group the small series into one, or split the chart. |
| `MISSING_ALT` | An image has no alt text, so a screen reader has nothing to say for it (WCAG 2.2 SC 1.1.1). | Write what the image shows between the brackets: `![The new north warehouse](assets/hero.png)`. |
| `TITLE_DUPLICATE` | Two slides have the same title; a screen reader lists slides by title, and PowerPoint's accessibility checker flags it (WCAG 2.2 SC 2.4.6). | Give each slide a title that says what that slide shows. |
| `COLOR_ONLY` | A chart's series or slices are told apart by color alone, which people with color blindness can't do (WCAG 2.2 SC 1.4.1). | Leave the legend on (the default for two or more series and for pies) or set `labels: true`. |
| `CVD_CONFUSABLE` | Two of the brand's chart colors look alike: the same color, or alike to people with a common color blindness (protanopia, deuteranopia or tritanopia), simulated on the colors themselves. | Ask the brand owner to change one of the two colors in tokens.yaml `chart.colors` or the theme accents; until then, label the series on charts that use both. |
| `TYPE_SMALL` | A size in `generate.type` is under the legibility floor for its mode: 18 pt for a projected deck, 12 pt for a read deck. | Raise the size in brand.yaml `generate.type` and regenerate the kit with `brand init <slug> --force`. |
| `MISSING_IMAGE` | An image path doesn't exist, or the image is a web address. | Fix the path; paths resolve relative to the deck file. Download a web image into the deck folder first. |
| `ASSET_OUTSIDE` | An image path resolves outside the deck's folder, or a brand asset outside its kit, through an absolute path, `..` or a symlink. A deck can't pull files from elsewhere on the machine into a deliverable. | Copy the image into the deck's folder and use its path relative to the deck file. |
| `BANNED_PATTERN` | Slide text or notes match one of the brand's banned patterns. | Reword the text. The pattern list is in the brand's brand.yaml under lint. |
| `MAX_SLIDES` | The deck has more slides than the brand allows. | Cut or merge slides. |
| `UNKNOWN_TOKEN` | A {{token}} in a bulk template has no matching data column. | Fix the token name or add the column to the data file. |
| `BAD_DATA_VALUE` | A bulk data cell holds a line break, or a value that would start a heading or image line where its {{token}} sits, which would change the deck's structure instead of filling in text. | Keep each cell to one line of plain text; put headings and images in the template, not the data. |
| `CSV_NO_SHEETS` | A CSV input references a chart or table sheet, which CSV can't hold. | Use an .xlsx workbook, or remove the sheet: reference. |
| `CONVERT_LOSSY` | The target format can't hold everything in the input, such as charts or code blocks in CSV. | Convert to .xlsx or .md instead. |
| `IMPORT_LOSSY` | The deck.md import wrote doesn't reparse to the same slides it extracted from the .pptx: some content, often in speaker notes, collided with deck.md's own syntax. | Open the named slide in deck.md, reword the colliding line, then run `deck-builder check`. |
| `KIT_STALE` | A generated kit no longer matches what made it: brand.yaml's palette, fonts or generate settings, or the logo on the master, changed after `brand init`, or a different deck-builder generated it. | Run `deck-builder brand init <slug> --force` to regenerate the kit from its own brand.yaml and assets. That replaces tuned budgets and edits made to the template in PowerPoint. |
| `LOW_CONTRAST` | Two brand colors that sit on each other don't meet WCAG 2.2 contrast: 4.5:1 for text (ink on background or surface, background on primary, links on background), 3:1 for icons and chart series. | Darken or lighten one color of the pair in the brand's palette, then `brand init` again. Change brand colors only with the brand owner's say-so. |
| `OVERFLOW_MEASURED` | Rendered text runs past its placeholder box. | Cut text in that field or split the slide, then rebuild and render again. |
| `EMPTY_PLACEHOLDER` | A rendered slide has a placeholder with no content. | Fill the field or use a layout without it. |
| `MISSING_FONT` | The renderer used another font than the brand's, or its fallback: the font isn't installed where the deck rendered. | Install the brand fonts where decks render. Don't change content to fit a substitute font; a PowerPoint render shows the real fonts. |
| `OFFICE_REPAIR` | PowerPoint couldn't open or export the built file, or stopped on a dialog such as a repair prompt. | A repair prompt on an engine-built file is an engine defect; report it with the input and manifest. |
| `RENDER_UNVERIFIED` | The PowerPoint render backend hasn't been verified on a real Mac yet. | Treat the render as provisional; run scripts/probe_powerpoint.sh to verify the backend. |
| `STALE_BUILD` | The deck source recorded in the .pptx's manifest was edited after the .pptx was built. | Rebuild the deck before trusting this render. |
| `SKILL_CONFLICT` | `skills install` found a file or folder where it would put a link, and left it alone. | Remove or rename the existing skill or agent if this clone's version should replace it, then rerun. |
