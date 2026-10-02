# Fictional brand asset fixtures

Three original, fictional companies for testing a presentation builder. Each brand folder contains raw image assets, a machine-readable `brand.yaml`, and a short brand guide. No slide decks or templates are included.

| Brand | Character | Heading / body font | Primary / accent |
| --- | --- | --- | --- |
| [Briarfield Paper Co.](brands/briarfield-paper/brand-guide.md) | Regional paper supplier | Georgia / Arial | `#23443D` / `#C99455` |
| [Cubicle Nine Systems](brands/cubicle-nine/brand-guide.md) | Office systems company | Avenir Next / Arial | `#293D59` / `#E89445` |
| [Afterhours Soapworks](brands/afterhours-soap/brand-guide.md) | Industrial small-batch soap | Helvetica Neue / Georgia | `#302F35` / `#D36F50` |

## Contents of each brand folder

- `brand.yaml`: Palette, theme color mapping, font families and fallbacks, and asset paths.
- `brand-guide.md`: Human-readable specifications and asset notes.
- `assets/logo.png` and `assets/logo-mono.png`: Transparent RGBA logos, 1600 x 368 pixels.
- `assets/icons/*.png`: Six transparent RGBA icons, 256 x 256 pixels: box, delivery, document, growth, people, and spark.
- `assets/hero.png`: Brand-specific RGB illustration, 2400 x 1350 pixels. The showcase deck uses copies in `showcase/assets/`, because a deck's images must sit inside its own folder.
- `assets/svg/*.svg`: Editable source art for every PNG.

Two decks use the brands. `showcase/deck.md` builds into all three with `build --data showcase/brands.csv` and makes the README images. `layouts/deck.md` puts every generated layout but `team` on a slide with realistic content, including the cases that used to look unfinished (a short list, a short table, a comparison, two columns), and the tests build and render it in all three brands. Cubicle Nine is a read-mode brand (decks sent and read on screen) and Afterhours Soapworks uses a dark big-number slide, so the `generate` options are exercised.

The PNGs are ready for image-placement tests; the SVGs allow source editing and rerendering. Fonts are specified by family and fallback, with no font binaries bundled. All names and artwork were made for these fixtures; they refer to no real company or film property.

## The scenario suite

These three brands cover one shape well: a full kit (logo, icons, SVG source, a long guide) skinning
the same deck three ways. `tests/scenarios/` covers the shapes this fixture set does not: an adopted
client template with its own renamed layouts, a kit with nothing but palette and fonts, a kit with far
more icons than any demo brand plus an unrelated `references/` folder, PNG-only vs. PNG-plus-SVG-source
icons, a long vs. a terse brand guide, decks from `deck.md`, `deck.xlsx` and a bulk CSV, an imported
`.pptx` with a hidden slide and speaker notes, a 3-slide deck vs. a 40-slide deck, and a deck folder with
a `source/` folder of grounding files beside one without. Every kit and `.pptx` those scenarios need is
generated at test time with python-pptx, Pillow and PyYAML, so none of it is checked in here.
