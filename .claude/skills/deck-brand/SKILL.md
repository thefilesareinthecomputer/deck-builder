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
approval, edits to `tokens.yaml`. You never write template XML.

`deck-builder docs brand-yaml` and `deck-builder docs tokens-yaml` are the formats. Read them
before writing either file.

## Pick the path with the user

| Path | When | Commands |
|---|---|---|
| Adopt | They have a template (`.potx` or `.pptx`) | `brand adopt <slug> --template FILE`, then fill in `brand.yaml` |
| Starter | They want something working now | A minimal `brand.yaml` (palette, fonts, logo), `brand init <slug> --from brand.yaml` |
| Full | They want the whole kit | Work through every section below, then `brand init` and the PowerPoint polish |

## Gathering the brand

Ask one topic at a time and show what you'll write before writing it.

- **Palette.** Named colors as 6-digit hex. Sources, best first: the brand guide, an existing
  deck (`brand adopt` reads its theme), colors the user pastes. Name colors by role (`primary`,
  `accent`, `ink`, `surface`), not by hue.
- **Theme slots.** Map `dk1`, `lt1`, `dk2`, `lt2`, `accent1` to `accent6`, `hlink`, `folHlink` to
  palette names. Text needs contrast against its background; flag pairs that look too close.
- **Fonts.** A heading and a body family, each with a fallback that ships with Office. Ask whether
  the fonts are licensed for embedding and installed on every machine that renders.
- **Logos.** PNG files with ids (`primary`, `mono`). Ask which one goes on the master, if any.
- **Icons.** PNG files, one per icon, file name = icon id. Record where they came from and their
  license in `icons.source`. Only use icon sets the user has the right to use.
- **Layout set.** `minimal`, `standard` or `full`; `deck-builder docs brand-yaml` lists what each
  holds. Ask what kinds of slides they make most.
- **Voice and lint.** Writing rules for the agent, and banned patterns the engine enforces.

## Generate, check, tune

```
deck-builder brand init <slug> --from brand.yaml   # or: brand adopt <slug> --template FILE
deck-builder brand check <slug> --json
deck-builder build <example deck> && deck-builder render <pptx> --json
```

Budgets in a generated `tokens.yaml` are estimates. Build a test deck with deliberately long
text, render it, and propose tighter or looser budgets per field from what overflowed. Change
`tokens.yaml` only after the user agrees.

## Polishing in PowerPoint

A generated template is clean but plain. For a premium look, the user edits it in PowerPoint:
`references/powerpoint-polish.md` is the walkthrough to give them. After any template edit, run
`deck-builder brand check <slug>`; if layouts or placeholders moved, `deck-builder inspect
<template> --yaml` shows the new mapping to fold into `tokens.yaml`.

Bump `version` in `brand.yaml` whenever a change affects output.
