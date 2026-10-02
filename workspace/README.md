# workspace

Your brands, decks and built files live here. Everything in this folder except this README is
gitignored, so nothing you put here can be committed to the deck-builder repo.

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
or an agent create as needed.

To keep a brand kit somewhere else, such as its own private repo, add its folder to
`brand_paths` in `deck-builder.toml`. Keep `workspace/` itself in its own private git repo for
history, rather than dated copies beside `deck.md`.
