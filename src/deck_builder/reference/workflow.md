# The build workflow, step by step

The engine owns layout, styling and validation. You write content; the engine checks and builds it.
The workspace folders, and who writes each, are listed at the end of this topic.

1. Pick a brand: `deck-builder brand list`, then `deck-builder brand show <slug>` for its layouts,
   fields and budgets. Only those layouts exist.
2. Write the deck as `deck.md` (`deck-builder docs deck-md`) or a workbook
   (`deck-builder docs workbook`). Set `brand: <slug>` in front matter.
3. Validate: `deck-builder check deck.md`. Fix every issue by editing content: cut words, split a
   slide, change layout. `deck-builder explain <CODE>` gives the cause and fix for any code.
4. Build: `deck-builder build deck.md`. It writes the .pptx and a .manifest.json beside it, in
   `workspace/out/` unless `-o` says otherwise.
5. Render and measure: `deck-builder render workspace/out/<deck>.pptx`. It lists flagged slides;
   look at those slide PNGs and the contact sheets, not every slide.
6. Fix flagged slides in the deck file, then repeat from step 3.

`deck-builder check deck.md --render` runs steps 3 to 5 in one command, and is the usual loop.

For an existing .pptx: `deck-builder import old.pptx <folder> --brand <slug>` turns it into
`deck.md`, its images and `import-report.md`, and the steps above rebuild it on the brand.
For one deck per data row: `deck-builder build deck.md --data rows.csv --name '{{client}}.pptx'`.

For team editing: `deck-builder convert deck.md deck.xlsx`, share the workbook, then
`deck-builder build deck.xlsx`. Converting back with `convert deck.xlsx deck.md` loses nothing.

Add `--json` to any command for one machine-readable object. Exit codes: 0 success,
1 validation issues, 2 usage or environment problems.

## Workspace folders

| Folder | Holds | Written by |
|---|---|---|
| `brands/<slug>/` | The brand kit: `brand.yaml`, `tokens.yaml`, `template.potx`, `assets/` | `brand init` or `brand adopt`, from the user's decisions |
| `brands/<slug>/references/` | Design reference decks, for inspiration only | The user; read-only for agents |
| `brands/<slug>/notes.md` | Working notes about the brand | The user or an agent, on request |
| `decks/<slug>/deck.md` | The deck's one content file (or `deck.xlsx`) | The user or an agent |
| `decks/<slug>/assets/` | Images the deck places | The user or an agent |
| `decks/<slug>/source/` | Source material for the deck, dated file names | The user; read-only for agents |
| `decks/<slug>/notes.md` | Working notes for the deck: decisions, open items, owner, status. Never the deck's speaker notes | The user or an agent |
| `out/` | Built `.pptx` files, manifests and renders | The engine only |
| `.cache/` | Derived assets such as recolored icons | The engine only |
| `scratch/` | Disposable intermediate output | Agents and skills; safe to delete anytime |

`deck-builder init` creates `brands/<slug>/`, `decks/<slug>/`, `out/` and `.cache/`; the rest you
or an agent create as needed. To keep a brand kit somewhere else, add its folder to `brand_paths` in
`deck-builder.toml`. For history, keep the workspace in its own git repo rather than dated copies
beside `deck.md`.
