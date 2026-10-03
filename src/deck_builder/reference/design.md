# Design rules for generated layouts and the decks written on them

The rules `brand init` builds into every generated kit, and the content rules that make a deck read well
on those layouts. The `deck-builder` and `deck-brand` skills read this topic before writing or styling.

## What the layouts do

- **One title position.** Every content slide puts its title in the same box, top left, bold, so the eye
  finds it without searching.
- **Type sized for how the deck is used.** `generate.mode` picks one of two documents. A `projected`
  deck (the default) is presented to a room: 32 pt titles, 24 pt single-column body, 20 pt for two
  columns, 18 pt tables, and nothing under 18 pt. A `read` deck is sent ahead and read on a screen,
  like a consultancy's leave-behind: 28 pt titles, a 14 pt body set to a 9 in measure (about 90
  characters a line), 13 pt columns, 12 pt tables, and text from the top of the body area.
  `generate.type` adjusts any single size.
- **Short content sits at the optical center.** A single-column body is centered in its area, a little
  above the middle of the slide, so three bullets don't hug the top and leave the lower half empty
  (`generate.body_anchor: top` turns this off).
- **Columns get structure.** Comparison columns sit on tinted panels with the heading inside; two-column
  slides get one thin divider. Nothing floats.
- **Tables are quiet.** A dark header row, thin rules between rows, no vertical lines, numeric columns
  right-aligned, and full content width directly under the title. Every column is at least as wide as
  its longest word, so no word breaks; the rest of the width follows content length. Five columns of
  short values fit a projected slide; more than that belongs in a read deck or an appendix.
- **Charts are native and quiet.** Bar and column value axes start at zero, and data labels sit on the
  data. Gridlines are hairlines in a faint tint, axis labels and the legend take the muted color, there
  are no tick marks, lines have no markers, and stacked segments are split by a hairline of the
  background. A bar or column chart with labels drops its value axis and gridlines, since each bar
  shows its own number. Horizontal bars list their categories top to bottom in the order written.
- **An optional takeaway.** Content, two-column, chart and table slides take a `takeaway:` field: one
  sentence in a full-width band in the primary color at the bottom, for the conclusion the slide
  supports. Leave it out and nothing is drawn.
- **One accent.** A short rule in the accent color on title, section, closing and big-number slides, and
  bullets and agenda numbers in the primary color. No other decoration.
- **Brand color in proportion.** Content slides are white with the brand color on titles, the table
  header and small accents; title, section and closing slides are full-bleed primary color.
- **Structure from shapes (designed set).** `layout_set: designed` adds layouts that draw their own
  structure: cards with colored label bands, process chevrons in a ramp of the primary color, and
  labeled bands. Every content slide gains a section label (`kicker:`) above the title and a
  one-line `subtitle:` under it, and comparison panels gain optional logo slots. **Bold** keywords
  on cards and bands take the primary color. `generate` options give icons a tile, process steps a
  white icon each, and the takeaway a quieter italic style (`docs brand-yaml`).

## Writing a deck that uses them well

- **One idea per slide, stated in the title.** Write the title as a sentence that states the conclusion
  ("Copy paper drove the growth"), not a label ("Volume"). One line is best, two at most. Read in
  order, the titles alone should tell the argument.
- **Vary the layout with the content.** A deck of table after table, or bullet list after bullet list,
  reads as a document. Match each point to the layout that shows it:

  | The point is | Use |
  |---|---|
  | One number that matters | `big-number` |
  | A trend or comparison of values | `chart` |
  | Two options, before and after, now and next | `comparison` or `two-col` |
  | Three parallel actions or ideas | `icon-row` |
  | A place, product or screen | `image` or `image-right` |
  | A voice from outside the team | `quote` |
  | Rows a reader will look up | `table`, six rows or fewer |
  | A short argument | `content`, four bullets or fewer |
  | Two to five parallel options, each with a few points (designed set) | `cards-2` to `cards-5` |
  | Three to six steps in order (designed set) | `process-3` to `process-6` |
  | Two to four themes, each with its points (designed set) | `bands-2` to `bands-4` |
  | The tools or companies a slide is about (designed set) | `logos` |
  | A query, config, command or function (full and designed sets) | `code`, or `code-right` beside bullets |

- **Digestible amounts.** Four bullets or fewer, each two lines at most, and about 40 words on a
  projected slide. Working memory holds about four chunks; the exact limits are convention. Move
  detail to speaker notes; the slide makes the point and the notes hold the evidence. `check` warns
  past these limits (`BULLETS_MANY`, `WORDS_MANY` at 60 words) and on more than three slides in a
  row on one layout (`LAYOUT_RUN`); a read deck skips the text limits.
- **Notes add, not repeat.** When the deck is presented, don't read the slide aloud: notes that
  repeat the slide word for word make it harder to follow. Reworded points or extra detail help.
- **Read decks: lines of 45 to 90 characters, about 55 as the target.** A projected slide is limited
  by its word count instead.
- **Say what the data means.** On a chart or table slide, put the conclusion in `takeaway:` so the reader
  doesn't have to work it out; use it on the slides that need it, not every slide.
- **Tables earn their place.** Use a table when the reader compares across rows. Cut columns that don't
  serve the point, and turn a two-row table into a sentence or a comparison.
- **Sources in the notes.** Put where each number came from in the slide's `Notes:`, so the slide stays
  clean and the claim stays checkable.
- **Pasted content gets the same treatment.** Text pasted in from documents, chats or other decks still
  goes through the fields of a layout: rewrite it to fit the budget instead of shrinking it to fit.

## Writing on slides

- Plain words and real numbers. An inflated word (leverage, seamless, robust), an intensifier standing in for
  a number (significantly, dramatically) or a filler transition (moreover, that said) says less than the plain
  word or the figure.
- A slide holds attention by setting up a real question with the data and answering it. State the point; a
  teaser ("here's the catch") withholds it.
- Keep "X, not Y" for the one or two beliefs the audience really holds; state the rest plainly.
- Type the plain characters: a spaced hyphen for a dash, straight quotes, three dots, `->`, and no emoji.
- `check` warns on all of these in slide text as `PROSE_TELL`; speaker notes, code and quoted words are left
  alone.

## Images, icons and logos

- Use icons for parallel ideas, one style and one color per deck, from the brand's icon set.
- Use vendor and product logos only where the slide is about that product, from the vendor's official
  artwork, unmodified and not recolored, with clear space around it.
- Use screenshots and photos at their real aspect ratio. The image layouts crop opaque images to fill
  their box, and fit images with transparent pixels (logos, icons) inside it, so a logo is never cut;
  in a large box a fitted logo takes at most 60% of it. Give a logo a transparent background to get
  the fit. Logo slots (comparison panels, the `logos` row) always fit, whatever the image.

## Charts

- Prefer bars and dots: position along a common scale is read most accurately. Show shares of a whole
  as a `bar` chart sorted largest first, not a pie or doughnut: lengths on one scale compare far more
  accurately than angles and areas. The engine still builds pie and doughnut charts, for imported decks.
- Keep a bar or column chart's value axis at zero; a cut axis makes small differences look large.
- Label the data directly where you can, rather than sending the eye to a legend.
- Eight colors at most in one chart. Color is never the only way to tell series apart: label them.
- Make the chart's title state what the data shows, and make sure the data shows it.

## Code

- Show only the lines that make the point: twelve or fewer on a projected slide (`check` warns past that
  with `CODE_LINES_MANY`), and put the full listing in the notes or an appendix.
- Mark the lines the slide is about with `{3,5-7}` and say what they do in the subtitle or takeaway; the
  highlight does the pointing, so the audience reads those lines first.
- Code never wraps, so break long lines where the language allows and keep names short; `check` reports a
  line wider than the panel as `CODE_LONG`. Use `code-right` when the code is short and the slide needs a
  few bullets of explanation; it holds about 40 characters a line on a projected slide.
- Add `lines` when you'll refer to lines by number, and `title=` when the file the code comes from matters.
- Code sits on a quiet panel that fits it, in the brand's code font at the code size (18 pt projected,
  12 pt read). Keywords are bold and comments italic, and every token color keeps 4.5:1 against the
  panel and the highlight band, so the code reads from the back of the room and in grayscale.

## Accessibility: contrast, color blindness and legibility

These rules come from a standard, WCAG 2.2 level AA, which is also what accessibility law points to
(US Section 508 cites WCAG 2.0 AA; the 2024 ADA Title II rule and the EU's European Accessibility
Act cite WCAG 2.1 AA). A deck that meets them reads for people with low vision, with color
blindness, or using a screen reader.

- **Contrast (SC 1.4.3, 1.4.11).** Text needs 4.5:1 against its background, or 3:1 at 18 pt and
  above or 14 pt bold; chart series, lines and icons need 3:1. Projectors lose contrast, so treat
  4.5:1 as the floor for body text. `brand check` reports `LOW_CONTRAST` for every pair a generated
  kit uses. `brand init` lightens the card, step and band ramp only as far as white labels keep
  4.5:1, writes a darker shade of the same hue into the chart palette for any brand color under 3:1,
  and gives chart labels white or ink, whichever reads on the bar or slice under them.
- **Color blindness (SC 1.4.1).** About 1 in 12 men can't tell some reds from greens. Color is never
  the only signal: chart series keep a legend or labels (`COLOR_ONLY`), status cells print their word
  beside the dot, and cards and steps have text labels. `brand check` simulates protanopia,
  deuteranopia and tritanopia on the chart colors and reports pairs that look alike
  (`CVD_CONFUSABLE`). The card, step and band ramp varies lightness, which every kind of color vision
  sees.
- **Size.** Nothing under 18 pt on a projected deck and nothing under 12 pt on a read deck; `brand
  check` reports a smaller `generate.type` size as `TYPE_SMALL`. Slide numbers and footers are the
  only smaller text.
- **Alt text (SC 1.1.1).** Every image says what it shows in `![alt](path)` (`MISSING_ALT`); charts
  and tables get alt text from their data, and brand icons are decorative.
- **Titles (SC 2.4.6).** Every slide has a title, and no two match (`TITLE_DUPLICATE`): a screen
  reader lists slides by title.

Everything else in this topic is convention or house style: good defaults, not laws.
