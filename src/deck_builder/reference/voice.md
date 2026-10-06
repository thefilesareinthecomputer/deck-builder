# Voice: how slide text and speaker notes read

Every agent that writes slide text writes by these rules, and the validator judges by them: the decomposer,
the storyteller, the builder and the main agent. They apply to titles, fields and speaker notes. The brand's
`voice:` lines in `brand show` add to them, and the user's own words come before both.

## The voice

- One colleague talking to another: the person who knows the work, explaining it to the people in the
  room. Write the way that person would say it out loud, in full, natural sentences.
- Use "we" statements that describe the session as it will happen, never bare commands. "We'll load the
  March orders, confirm the row counts match the warehouse, then rerun to show nothing is duplicated" reads
  as a person; "Load orders. Check counts." reads as a checklist. "When a delivery is late, this report is
  the first place we look" beats "Look here first when a delivery is late".
- Name the real thing: the table, the file, the tool, the team (`orders.daily_summary`, "the store's YAML
  file", "the Ridgeview store"). Generic nouns such as "the framework", "the configuration" or "a row"
  make the reader guess.
- Give the reason a step matters: "We request the service account in week one, because approval takes
  two weeks and the load can't start without it."
- Accuracy comes before tidiness. A rewrite keeps every fact, name and number of the line it replaces;
  when you aren't sure a reworded fact still holds, keep the source's wording and flag it in your report.

## Sentences

- Every title, bullet, subtitle, takeaway and speaker note is a full sentence with a subject and a verb.
  The one exception is a quick-reference slide, such as recovery steps or a checklist, where short
  `label: fix` lines read best.
- A title states the slide's point ("Testers cost a pilot store $2.40 a week"), never a topic ("Tester
  costs").
- Kickers and labels locate ("Q3 delivery"); they don't argue.
- A subtitle can be warm and plain ("It takes a whole team to open a new store") when it says what the
  slide is about.

## Fitting text to a slide

Choose each slide's layout from how much its point needs to say, then write full sentences into it. When
`check` reports `BUDGET_LINES` or `BUDGET_CHARS`, the text and the layout don't match:

- Move the text to a layout with room for it (the message names the layouts that hold it as written), split
  the slide, or move detail to the speaker notes.
- Cut only whole points, never words out of a sentence. A field that can't hold a full sentence belongs on
  another layout.
- A title over its budget becomes a shorter full sentence, or moves to a layout with a bigger title budget.
  It never drops its verb or changes its claim.

## Slides stand alone

Slides get reordered and pasted into other decks. Never write "previous slide", "next slide", "slide 20",
"the slide above" or "see above" in slide text or notes; name what that slide shows instead ("the weekly
sales chart"). `check` warns `SLIDE_REF`.

## Speaker notes

- Notes are the presenter's script: what they say, in full sentences, with more detail than the slide. They
  never contradict the slide.
- Sources go on a closing `Source:` line that names a document the audience could open
  (`pilot-sales.csv`, "the March store survey"). Never cite `outline.md`, a storyboard or an item number:
  those are working drafts, and the notes ship inside the .pptx.
- Image cue lines (`SCREENSHOT:`, `DIAGRAM:`) stay as `docs deck-md` describes.

## Cut, don't caveat

No warning or negative bullets on a slide ("A green run doesn't mean every store reported"). State the
check we run instead ("We confirm each store's row count after the run"), or cut the line.

## What never goes on a slide

- Compelling comes from the order of the slides and from real numbers, never from phrasing. Tension is a
  real question the data sets up before its answer. No teasers or hooks ("the surprising part is", "here's
  the catch", "and the last one changes everything"), no withheld facts, no clickbait.
- Plain words. No inflated vocabulary (leverage, utilize, unlock, empower, seamless, robust, holistic,
  journey, landscape, ecosystem, game-changing, cutting-edge), no intensifiers in place of a number
  (significantly, dramatically, incredibly, crucially), and no filler transitions (moreover, that said, in
  conclusion, let's dive in).
- Cadence. At most two "X, not Y" contrasts in a whole deck, each correcting a belief the audience really
  holds; state the rest as plain assertions. No "not only X but also Y", no rhetorical questions as titles,
  no self-answering setups, and no padded third item: a list holds as many items as the content has.
- Register. No verbless fragments or two-word imperatives used for weight, no slogans or aphoristic
  closers, no coined phrases where a standing term exists, and no figures that inform no decision.
- Truth. No invented specifics, no negatives ("the only supplier", "no other way") the sources don't
  establish, no fourth item because three felt short, and nothing planned presented as done.
- Symbols. No em dashes, curly quotes, ellipsis characters, arrows or emoji in slide text.
- Emphasis. One bold phrase per field at most; the order of the text does the rest.

`check` warns on the countable ones as `PROSE_TELL`. A clean `check` isn't a clean read.

## The user's own words

- A line the user wrote stays as written, such as a warm subtitle or an idiom. These bans apply to agent
  text.
- Once the user edits the built .pptx by hand, that file is the deck. Never rebuild over it or overwrite
  their edits. Learn the rules their edits show, and write new slides by them (the `deck-builder` skill
  has the steps).

## Rewriting slides that exist

- Read each line once against all of these rules together, and rewrite it whole. A pass per rule misses
  what one read catches.
- Before a wording pass over slides the user already has, the user sees each changed line, old and new, and
  approves it first. An agent asked for a wording pass returns that table instead of editing.
