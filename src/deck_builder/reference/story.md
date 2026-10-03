# Storytelling: the arc, the pacing and the visual form of a deck

How a set of points becomes a deck an audience follows and remembers: the order, the one point per slide,
the visual form each slide takes, and the pacing between slides. The `deck-storyteller-agent` applies these
rules and writes them down as a storyboard; the builder writes the deck from that storyboard, and the
validator checks the deck against it. `docs design` has the layout rules these build on.

## The storyboard

`storyboard.md` sits in the deck folder. A header names the audience, the goal, the arc, the tone and the
slide count; then one frame per slide, in order:

```markdown
## 4. Capping each week at three times the median removed the spike
beat: resolution
part: 2 of 3, The fix
layout: code
focus: lines 4-5
emphasis: "three times the median"
visual: none
after: a close-up on the cause, after the establishing chart on slide 3
notes: Lines 4 and 5 are the fix; the chart on slide 3 shows the spike. Source: outline.md, item 7.
```

| Key | What it holds |
|---|---|
| heading | The slide's number and title: one sentence that states the point |
| `beat` | The slide's job in the arc: setup, complication, turn, evidence, resolution or call to action |
| `part` | For a deck in parts: which part, and its name (see "Map and parts") |
| `layout` | A layout from `brand show` |
| `focus` | The one thing the eye lands on first: a number, a phrase, an image, a chart's key bar, highlighted lines |
| `emphasis` | The phrase to bold, at most one per field, or `none` |
| `visual` | `none`, `icon brand:icon/<id>`, `chart <type>: <the comparison>`, or `image: <what it must show, and why>` |
| `motion` | `none`, or `fade <field>` or `fade slots`: the parts appear one click at a time (`build:` in deck.md) |
| `after` | How the slide follows the previous one (the transitions below) |
| `notes` | What the presenter says, and the source of every number on the slide |

The builder fits each title to its budget and may shorten it, but never changes what it claims. An image cue
names a picture the user supplies; nothing is downloaded or generated.

## The title spine

Read in order, the titles alone tell the argument. Write them first, before choosing any layout: if the
spine doesn't persuade on its own, no visual will rescue it. Each title is a full sentence stating a
conclusion ("Capping outliers fixed the forecast"), not a topic ("Forecast fix").

## Choosing the arc

| Goal | Arc |
|---|---|
| Recommend a decision | Situation, complication, resolution: what is true, what changed or broke, what to do |
| Win support for a change | What is, then what could be, alternating, ending on the call to action |
| Report results | The headline result first, then the evidence by section, then what's next |
| Explain how something works | An establishing view, then each part close up, then the whole again |
| Teach | One idea per slide, each built on the last, with a worked example before the rule |

## Map and parts

A deck past about 15 slides works best as a map and its parts. An overview slide (an `agenda`, cards or a
process) names three to five parts; each part is a short series of three to six sub-slides; and each series
opens by returning to the map with its own part marked. The audience always knows where they are and how
much is left.

- Every sub-slide of a part shares one kicker, the part's name, so the section label does the wayfinding.
- On the returning map slide, `current: n` marks the part: on an `agenda` (or any list) every other item
  takes the muted color, and on `cards-N` every other card's label loses its color, so the part is the one
  thing in full color.
- Each part ends on its own conclusion, in a takeaway or a `big-number` or `quote` slide, and the closing
  slide states each part as its conclusion.
- A part that needs more than six sub-slides is two parts.

## Pacing from slide to slide

Comics name the step between two panels, and the same steps work between slides. Choose each one on purpose
and write it in `after`:

- **Establishing shot, then close-up.** The whole (a chart of the year, the process, the map) before a
  detail of it. The audience needs the frame before the detail means anything.
- **Moment to moment.** The same view, one thing changed: the same chart with the next quarter added, the
  same code with the next lines highlighted. Use it for a change you want noticed. Inside one slide,
  `motion: fade` does the same: steps, cards or items appear one click at a time, so the presenter sets
  the pace. Use it on a few slides where the order is the point, never as decoration.
- **Subject to subject.** A different view of the same idea: the number, then the customer it happened to.
- **Scene to scene.** A jump to the next part; mark it with a section slide or the returning map.
- **Closure.** When the step between two slides is obvious, leave it out and let the audience make it.
- **One splash.** The single most important slide gets the biggest treatment (`big-number`, `statement`, a
  large image on `image`, a `quote`), and only one slide in a deck gets it.

Alternate dense and sparse slides: a table or a chart, then a slide with one number or one sentence. Three
slides in a row on one layout read as a document (`check` warns as `LAYOUT_RUN`).

## One idea per slide

Animation's working rules apply to slides:

- **Staging.** One clear idea per slide, placed where the eye goes first.
- **Anticipation.** Set up the question with the real data before the answer: the chart of the spike before
  the code that fixed it.
- **Exaggeration, once.** The one number the deck is about gets the biggest type in the deck; no other
  number competes with it.
- **Timing.** Spend slides where the audience needs time: a hard idea gets two slides, an easy one gets a
  line in another slide's notes.
- **Follow-through.** A later slide calls back to an earlier number, image or phrase, so the deck feels
  built rather than listed.

## Emphasis and type

Type size is a property of the layout, so emphasis by size goes through the layout:

| To make this stand out | Use |
|---|---|
| One number | `big-number` |
| One sentence: the turn, the conclusion of a part, the ask | `statement`, with its one bold phrase in the primary color |
| A voice from outside the team | `quote` |
| A short phrase inside a field | `**bold**`, one phrase per field, in the primary color on cards and bands |
| The lines of code the slide is about | `{3,5-7}` on the code block |
| Where the slide sits in the deck | `kicker:`, the small label above the title |
| The so-what under the title | `subtitle:` |
| The conclusion of a chart or table | `takeaway:` |

One focal point per slide; every other element is quieter than it. Scale contrast, alignment and white space
do the work that boxes, rules and color would otherwise be added for.

## Picture, icon, chart or nothing

- **A photo** for a place, a product, a person or a moment the audience should see: one per slide, at its
  real aspect ratio, never as decoration.
- **An icon** for parallel ideas (`icon-row`, process steps): one icon set and one color per deck.
- **A chart** for a comparison of values: bars for amounts and shares, a line for change over time. State
  the comparison in the title.
- **Nothing** when one sentence says it: a `big-number` or a short `content` slide.

## Tension from the facts

A deck holds attention by setting up a real question with the data and answering it, in that order. It never
withholds a fact to manufacture suspense or teases what comes next ("the surprising part is", "here's the
catch"): the title states the point, and the order of the slides creates the pull.

## Tone

The storyboard header sets the tone, always within the brand's `voice` rules:

- **`plain`** (the default): professional, direct, no motif.
- **`warm`**: the same rules, with one human example (a customer, a site, a day in the work) that recurs
  across the deck.
- **`bold`**: the same rules, with one recurring visual motif (an image, an icon or a phrase used at the
  start, the turn and the close) and stronger contrast between sparse and dense slides.

No tone changes the writing rules: titles still state the point in plain words, and every number still has a
source.
