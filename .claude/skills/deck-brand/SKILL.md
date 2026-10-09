---
name: deck-brand
description: >-
  Works with the user to create or change a deck-builder brand kit - palette and hex codes,
  theme color slots, fonts, logos, icons, the layout set, voice and lint rules - by writing
  brand.yaml and running the deck-builder brand commands. Use when setting up a new brand or
  client template, adopting an existing .potx or .pptx, adding a layout, changing colors or
  fonts, sourcing icons, tuning budgets after a test render, or polishing a generated template
  in PowerPoint. Also runs as the brand step of onboarding. Not for writing slide content.
license: MIT
---

# deck-brand

A brand kit is the design system: `brand.yaml` (what the user decides), `tokens.yaml` (the
contract the engine checks against) and the template. This skill is a conversation with the
user; the engine generates and validates. You write `brand.yaml` and, with the user's
approval, edits to `tokens.yaml`. You never write template XML. Styling always goes into the
kit; an engine change under `src/` is a separate task, started only when the user asks, with
tests (see AGENTS.md).

`deck-builder docs brand-yaml` and `deck-builder docs tokens-yaml` are the formats, and
`deck-builder docs design` is the design standard the generated layouts follow. Read them before
writing either file yourself; the `deck-brand-agent` reads them on its own when it does the writing.

## Pick the path with the user

| Path | When | Commands |
|---|---|---|
| Adopt | They have a template (`.potx` or `.pptx`) | `brand adopt <slug> --template FILE`, then `inspect FILE` to read each layout's placeholder types, rename the generated layout keys and fields in `tokens.yaml` to what they're for, and fill in `brand.yaml` |
| Starter | They want something working now | A minimal `brand.yaml` (palette, fonts, logo), `brand init <slug> --from brand.yaml` |
| Full | They want the whole kit | Work through every section below, then `brand init` and the PowerPoint polish |

## Gathering the brand

Ask one topic at a time and show what you'll write before writing it.

- **Palette.** Named colors as 6-digit hex. Sources, best first: the brand guide, an existing
  deck (`brand adopt` reads its theme), colors the user pastes. Name colors by role (`primary`,
  `accent`, `ink`, `surface`), not by hue.
- **Theme slots.** Map `dk1`, `lt1`, `dk2`, `lt2`, `accent1` to `accent6`, `hlink`, `folHlink` to
  palette names. Don't judge contrast by eye: `brand_check` reports `LOW_CONTRAST` for any pair
  under the WCAG 2.2 threshold once the kit exists. After a color change, pass on each one it
  reports as it reports it, with the ratio, rather than summarizing them.
- **Fonts.** A heading and a body family, each with a fallback that ships with Office. Ask whether
  the fonts are licensed for embedding and installed on every machine that renders.
- **Logos.** PNG files with ids (`primary`, `mono`). Ask which one goes on the master, if any.
- **Icons.** PNG files, one per icon, file name = icon id. Record where they came from and their
  license in `icons.source`. Only use icon sets the user has the right to use.
- **Layout set.** `minimal`, `standard`, `full` or `designed`; `deck-builder docs brand-yaml` lists
  what each holds. Ask what kinds of slides they make most. `designed` suits decks that need cards,
  process steps or section labels on every slide.
- **Type and placement.** Ask whether decks are mostly projected or read on screen. The defaults in
  `generate.type` suit projection; a leave-behind document takes smaller sizes. A brand that
  prefers dark emphasis slides can set `generate.big_number: dark`. If they have past decks they
  consider good, render them and match their sizes in `generate.type` rather than editing the
  template.
- **Voice and lint.** Writing rules for the agent, and banned patterns the engine enforces.

## Generate, check, tune

Once the decisions are made, hand the mechanical work to the `deck-brand-agent` subagent: the
slug, the decisions, and the paths of the brand guide, template, logos and icons. It writes
`brand.yaml`, generates or adopts the kit, checks it, test-renders it and returns proposed
budgets and questions. Relay the questions, get the user's answers, and send them to the same
agent with SendMessage if needed.
It has no shell and runs the engine through nine MCP tools, which read only inside the workspace and
the `brand_paths` folders (the full map is `deck-builder docs agents`): copy the user's guide,
template, logos and icons into a scratch folder in the workspace first, and give it those paths.
The commands it runs, for doing it here instead:

Run the CLI as `uv run deck-builder` inside the deck-builder clone, or `deck-builder` where it's
installed (`db` below).

```
db brand init <slug> --from brand.yaml    # or: db brand adopt <slug> --template FILE
db brand check <slug> --json              # must pass before any deck uses the brand
db brand show <slug>                      # what a deck writer will see
db check <test deck> --render --json      # build, render, measure
```

For a new kit, write the user's `brand.yaml` somewhere outside the kit first (the workspace's
`decks/` or a scratch folder), then `brand init` copies it and its assets into
`workspace/brands/<slug>/`. To change an existing kit (a color, a font), edit the kit's own
`brand.yaml` and run `brand init <slug> --force` with no `--from`; nothing needs copying. The backup
it takes holds your edited `brand.yaml`, so tell the user each value you changed, old and new. A kit
change reaches every deck on that kit, so when other decks use it and the user means one deck,
`brand copy` it first and point that deck at the copy. `brand init --force` regenerates `template.potx` and `tokens.yaml` from scratch, replacing tuned
budgets and any PowerPoint polish. It first copies the whole kit into `<kit>/backups/<time>/` and
reports that path and the budgets that changed: tell the user, and offer to copy back the ones they
tuned. To rename or version a brand, `brand copy <slug> <new-slug>` copies the whole kit under the
new slug and leaves the original alone; then point the decks' `brand:` at the new slug.

Budgets in a generated `tokens.yaml` are estimates. Build a test deck that fills each layout's
text fields to their budgets, run `check --render`, and propose tighter or looser budgets per field
from the `OVERFLOW_MEASURED` results. Change `tokens.yaml` only after the user agrees, then render the
test deck once more and report any remaining overflow to the user.

Fonts: `MISSING_FONT` means the brand font isn't installed on the machine that rendered. Install it
before tuning budgets, since budgets measured with a substitute font are wrong.

## Polishing in PowerPoint

A generated template is clean but plain. For a premium look, the user edits it in PowerPoint:
`references/powerpoint-polish.md` is the walkthrough to give them. After any template edit, run
`db brand check <slug>`; if layouts or placeholders moved, `db inspect <template> --yaml` shows
the new mapping to fold into `tokens.yaml`.

Bump `version` in `brand.yaml` whenever a change affects output.
