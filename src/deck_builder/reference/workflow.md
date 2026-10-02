# The build workflow, step by step

The engine owns layout, styling and validation. You write content; the engine checks and builds it.
`workspace/README.md` lists the workspace folders and who writes each.

1. Pick a brand: `deck-builder brand list`, then `deck-builder brand show <slug>` for its layouts,
   fields and budgets. Only those layouts exist.
2. Write the deck as `deck.md` (`deck-builder docs deck-md`) or a workbook
   (`deck-builder docs workbook`). Set `brand: <slug>` in front matter.
3. Validate: `deck-builder check deck.md`. Fix every issue by editing content: cut words, split a
   slide, change layout. `deck-builder explain <CODE>` gives the cause and fix for any code.
4. Build: `deck-builder build deck.md`. It writes the .pptx and a .manifest.json beside it.
5. Render and measure: `deck-builder render out/deck.pptx`. It lists flagged slides; look at those
   slide PNGs and the contact sheets, not every slide.
6. Fix flagged slides in the deck file, then repeat from step 3.

For team editing: `deck-builder convert deck.md deck.xlsx`, share the workbook, then
`deck-builder build deck.xlsx`. Converting back with `convert deck.xlsx deck.md` loses nothing.

Add `--json` to any command for one machine-readable object. Exit codes: 0 success,
1 validation issues, 2 usage or environment problems.
