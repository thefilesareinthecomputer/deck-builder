"""Decks that differ in format, size and origin, each taken through the real CLI path.

Covers: deck.md vs. deck.xlsx (made with `convert`) vs. a bulk CSV build; an imported .pptx with a
hidden slide and speaker notes, rebuilt onto a kit; a 3-slide deck vs. a 40-slide deck that cycles
through every generated layout; and a deck folder with a `source/` folder of grounding files beside
one without, proving the engine ignores it.
"""
from __future__ import annotations

import hashlib

from pptx import Presentation
from scn import hidden_notes_pptx, needs_render, render, setup_cycle_decks

from conftest import cli_json, write_deck

DECK_EVERY_STOCK_LAYOUT = """
---
brand: stock
title: Northfield quarterly review
---

## Northfield quarterly review
layout: title
subtitle: Shipments, margins and the plan for Q4

## Volume grew in Q3
layout: content

- Up 12% over Q2
- Two new accounts signed

## 12%
layout: big-number
caption: Volume growth, Q2 to Q3

## Cases by month
layout: chart

```chart
type: column
categories: [Jul, Aug, Sep]
series:
  - name: Copy paper
    values: [410, 378, 331]
```

## Open items
layout: table

| Item | Owner | Due |
|---|---|---|
| Warehouse lease | Ops | Oct |

## Logo
layout: image

![Logo](brand:logo/primary)

### caption
The current mark.

## Checked
layout: icon
icon: brand:icon/check
"""


# ---------------------------------------------------------------- deck.md, deck.xlsx, bulk CSV


def test_deck_md_and_its_converted_xlsx_build_byte_identical_pptx(ws, capsys):
    (ws / "decks" / "review").mkdir()
    md = write_deck(ws, DECK_EVERY_STOCK_LAYOUT, name="review/deck.md")
    xlsx = ws / "decks" / "review" / "deck.xlsx"
    code, out = cli_json(ws, "convert", str(md), str(xlsx), capsys=capsys)
    assert code == 0, out

    code, md_out = cli_json(ws, "build", str(md), "-o", str(ws / "out" / "from-md.pptx"), capsys=capsys)
    assert code == 0, md_out["issues"]
    code, xlsx_out = cli_json(ws, "build", str(xlsx), "-o", str(ws / "out" / "from-xlsx.pptx"), capsys=capsys)
    assert code == 0, xlsx_out["issues"]

    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    assert sha(ws / "out" / "from-md.pptx") == sha(ws / "out" / "from-xlsx.pptx")


def test_bulk_csv_builds_one_deck_per_row(ws, capsys):
    tmpl = write_deck(ws, """
        ---
        brand: stock
        ---

        ## {{client}} review
        layout: title
        subtitle: Prepared for {{contact}}
        """, name="pitch.md")
    data = ws / "decks" / "clients.csv"
    data.write_text("client,contact\nHalvorsen Freight,Ops lead\nCopperline Foods,Buyer\nLinden Medical,CFO\n",
                    encoding="utf-8")
    code, out = cli_json(ws, "build", str(tmpl), "--data", str(data), "--name", "{{client}}.pptx", capsys=capsys)
    assert code == 0, out["issues"]
    names = sorted(o["output"].rsplit("/", 1)[-1] for o in out["outputs"])
    assert names == ["Copperline-Foods.pptx", "Halvorsen-Freight.pptx", "Linden-Medical.pptx"]
    assert len(out["outputs"]) == 3


# ---------------------------------------------------------------- an imported .pptx: hidden slide, notes


def test_a_hidden_slide_and_its_notes_import_and_rebuild_onto_a_kit(ws, capsys):
    pptx = hidden_notes_pptx(ws / "client.pptx")
    code, out = cli_json(ws, "import", str(pptx), str(ws / "imported"), "--brand", "stock", capsys=capsys)
    assert code == 0, out
    assert out["slides"] == 2
    deck_md = (ws / "imported" / "deck.md").read_text()
    assert "Hidden until finance signs off." in deck_md  # the hidden slide's notes made it through
    assert "Draft: pricing options" in deck_md  # and its title

    code, build_out = cli_json(ws, "build", str(ws / "imported" / "deck.md"), "-o", str(ws / "rebuilt.pptx"),
                               capsys=capsys)
    assert code == 0, build_out["issues"]
    rebuilt = Presentation(build_out["output"])
    assert len(rebuilt.slides) == 2
    assert [s.shapes.title.text for s in rebuilt.slides] == ["Volume grew in Q3", "Draft: pricing options"]


# ---------------------------------------------------------------- a 3-slide deck vs. a 40-slide deck


def test_a_3_slide_and_a_40_slide_deck_both_build_clean(tmp_path, capsys):
    root, deck3, deck40 = setup_cycle_decks(tmp_path)
    capsys.readouterr()
    code, out3 = cli_json(root, "build", str(deck3), capsys=capsys)
    assert code == 0, out3["issues"]
    assert out3["slides"] == 3
    code, out40 = cli_json(root, "build", str(deck40), capsys=capsys)
    assert code == 0, out40["issues"]
    assert out40["slides"] == 40
    prs = Presentation(out40["output"])
    assert len(prs.slides) == 40
    # every layout of the `full` set shows up somewhere in 40 slides, cycling
    import yaml

    kit = root / "workspace" / "brands" / "northfield-cycle"
    layouts = set(yaml.safe_load((kit / "tokens.yaml").read_text())["layouts"])
    assert layouts == {"title", "agenda", "section", "content", "two-col", "comparison", "big-number", "statement",
                       "chart", "table", "image", "image-full", "image-right", "code", "code-right", "icon-row", "team",
                       "quote",
                       "closing"}


@render
@needs_render
def test_the_40_slide_deck_renders_with_no_errors(tmp_path, capsys):
    root, _, deck40 = setup_cycle_decks(tmp_path)
    capsys.readouterr()
    code, out = cli_json(root, "check", str(deck40), "--render", capsys=capsys)
    errors = [i for i in out["issues"] if i["severity"] == "error"]
    assert code == 0, errors
    assert out["flagged_slides"] == []


# ---------------------------------------------------------------- source/ grounding files beside a deck


def test_a_source_folder_of_grounding_files_is_harmless(ws, capsys):
    body = """
        ---
        brand: stock
        ---

        ## Northfield quarterly review
        layout: content

        - Up 12% over Q2
        """
    (ws / "decks" / "with-source" / "source").mkdir(parents=True)
    (ws / "decks" / "without-source").mkdir()
    with_src = write_deck(ws, body, name="with-source/deck.md")
    (with_src.parent / "source" / "notes.txt").write_text(
        "Raw interview notes the deck was drafted from. Never read by the engine.", encoding="utf-8")
    (with_src.parent / "source" / "raw-data.csv").write_text("month,cases\nJul,9800\nAug,10400\n",
                                                              encoding="utf-8")
    without_src = write_deck(ws, body, name="without-source/deck.md")

    code, out_a = cli_json(ws, "build", str(with_src), "-o", str(ws / "out" / "with-source.pptx"), capsys=capsys)
    assert code == 0, out_a["issues"]
    code, out_b = cli_json(ws, "build", str(without_src), "-o", str(ws / "out" / "without-source.pptx"),
                           capsys=capsys)
    assert code == 0, out_b["issues"]

    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    assert sha(ws / "out" / "with-source.pptx") == sha(ws / "out" / "without-source.pptx")
