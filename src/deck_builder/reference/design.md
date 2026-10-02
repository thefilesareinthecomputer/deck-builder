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
- **Charts are native.** Bar and column value axes start at zero, and data labels sit on the data.
- **An optional takeaway.** Content, two-column, chart and table slides take a `takeaway:` field: one
  sentence in a full-width band in the primary color at the bottom, for the conclusion the slide
  supports. Leave it out and nothing is drawn.
- **One accent.** A short rule in the accent color on title, section, closing and big-number slides, and
  bullets and agenda numbers in the primary color. No other decoration.
- **Brand color in proportion.** Content slides are white with the brand color on titles, the table
  header and small accents; title, section and closing slides are full-bleed primary color.

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

- **Digestible amounts.** Four bullets or fewer, each two lines at most, and about 40 words on a
  projected slide. Working memory holds about four chunks; the exact limits are convention. Move
  detail to speaker notes; the slide makes the point and the notes hold the evidence.
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

## Images, icons and logos

- Use icons for parallel ideas, one style and one color per deck, from the brand's icon set.
- Use vendor and product logos only where the slide is about that product, from the vendor's official
  artwork, unmodified and not recolored, with clear space around it.
- Use screenshots and photos at their real aspect ratio; the image layouts crop photos to fill and fit
  logos and icons inside.

## Charts

- Prefer bars and dots: position along a common scale is read most accurately. Use a pie only for a
  few shares of one whole.
- Keep a bar or column chart's value axis at zero; a cut axis makes small differences look large.
- Label the data directly where you can, rather than sending the eye to a legend.
- Eight colors at most in one chart. Color is never the only way to tell series apart: label them.
- Make the chart's title state what the data shows, and make sure the data shows it.

## Contrast

Contrast is the one rule here backed by a standard (WCAG 2.2). Text needs 4.5:1 against its
background, or 3:1 at 18 pt and above or 14 pt bold; that 18 pt is a contrast tier, not a size
minimum. Chart series, lines and icons need 3:1 against their background. Projectors lose contrast,
so treat 4.5:1 as the floor for body text. `brand check` reports `LOW_CONTRAST` for the pairs a
generated kit uses.

Everything else in this topic is convention or house style: good defaults, not laws.
