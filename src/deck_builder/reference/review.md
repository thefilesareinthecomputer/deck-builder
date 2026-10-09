# Review checklist: what a built deck is judged on before anyone calls it finished

The `deck-validator-agent` judges every built deck against this list, and the `deck-builder-agent` goes
over its draft with it before writing the deck file, so a deck passes review the first time. It covers
what `check` can't measure; `check` enforces budgets, field kinds, assets and the brand's lint rules.
The rules it draws on are in `docs design` and `docs voice`.

**Storyline and titles**
- Each content title is a sentence that states the point, unique in the deck, one line at best and
  two at most; read in order, the titles alone tell the argument, and they match the approved
  storyline.
- Kickers, where the layouts have them, are short, worded the same way for the same section, and
  present on every content slide. A subtitle adds the so-what rather than repeating the title.
- With a storyboard: the deck keeps its order, layouts, focal points and bold phrases, each title
  claims what its frame's title claims, and the one splash slide is the one the storyboard names.
- The closing slide asks for something concrete: who decides what, and by when.

**Consistency**
- One name per thing: products, teams, units, abbreviations, capitalization.
- One format per kind of number: percentages, currency, thousands separators, dates, ranges.
- Numbers agree across slides, tables, charts, takeaways and notes; totals add up; shares of one
  whole come to about 100%.
- Parallel sets read as sets: cards, process steps, bands, columns and comparison sides use the
  same grammatical form, similar lengths and, where it reads as a set, the same number of points.
- Every number on a slide has its source in that slide's speaker notes.

**Layout and rhythm**
- Each slide's layout fits its point (the table in `docs design`): one number as big-number, a
  trend as a chart, steps as process, parallel options as cards or comparison.
- Sections are paced; no stretch of the same layout; nothing reads as a document pasted onto slides.
- A takeaway sits on the chart and table slides that need one, says what the data means, and the
  data on the slide shows it.

**Images**
- An image shows what its alt text, its cue and the slide's claim say it shows. A generic or
  stand-in picture beside a specific claim (a product shot where the slide names one store's shelf)
  reads as evidence it isn't; when no supplied image fits, the slide uses a layout without one and
  the missing image goes to the user as a request.

**What the renders show**
- Nothing overlaps, crosses its shape, is cut off, or sits off its grid; no slide is mostly empty or
  crowded; a title or label doesn't strand one short word on its last line where a small rewording
  fixes it.
- Images and logos are undistorted and uncropped, with clear space, and logos appear only where the
  slide is about that product or company. Every captured image is on its slide; one the image list
  shows as notes only is there on purpose, or it's a finding.
- Charts read at a glance: bars start at zero, series are labeled, colors are told apart.
- Code reads from the back of the room: no line runs past its panel, the block is the few lines that
  make the point, and the highlighted lines are the ones the title or takeaway explains.
- Nothing is hard to read: light text on a light fill, or small text on a busy image.

**Language**
- Typos, grammar, doubled words, mixed tense, and anything against the brand's voice rules.
- No placeholder text, `TODO`, sample text or unfilled `{{tokens}}`.
- Every rule in `docs voice`, read once per line against all of them together: full sentences, the
  real names, slides that stand alone, notes that are the presenter's script and agree with the slide.
  Text the user wrote is theirs: it changes only when it's wrong.

**Accessibility (the WCAG 2.2 AA section of `docs design`)**
- Every image has alt text that says what it shows, not "image" or the file name.
- Color is never the only way a point is made: series are labeled or in a legend, and a status or
  category named in color is also named in words.
- Nothing is too small or too faint to read for someone with low vision: text on a photo, light text
  on a tint, a chart label on a dark bar. `check` and `brand check` warnings on contrast, color
  blindness and size (`LOW_CONTRAST`, `CVD_CONFUSABLE`, `TYPE_SMALL`, `COLOR_ONLY`, `MISSING_ALT`,
  `TITLE_DUPLICATE`) are findings, at least major.
