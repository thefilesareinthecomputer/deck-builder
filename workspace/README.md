# workspace

Your brands, decks and built files live here. Everything in this folder except this README is
gitignored, so nothing you put here can be committed to the deck-builder repo.

`deck-builder init` creates:

```
workspace/
  brands/<slug>/    brand kits: brand.yaml, tokens.yaml, template.potx, assets/
  decks/<slug>/     deck.md or deck.xlsx, plus assets/
  out/              built .pptx files, manifests and renders
  .cache/           derived assets such as recolored icons
```

To keep a brand kit somewhere else, such as its own private repo, add its folder to
`brand_paths` in `deck-builder.toml`.
