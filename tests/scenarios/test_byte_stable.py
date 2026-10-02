"""Byte-stable builds: the same deck, built in two separate workspaces that never share a file,
produces the identical .pptx, embedded chart workbook included.

tests/unit/test_build.py's test_rebuild_is_byte_identical already proves a rebuild in the same
workspace is byte-identical; this proves the same thing holds across two workspaces that share
nothing (a different kit copy, a different tmp root), which is the shape that actually matters for
agents: two different runs, on two different machines, must produce the same bytes.

Each workspace generates its own copy of the kit from the same brand.yaml with `brand init`, rather
than sharing a kit folder, so the comparison is honest: it is `brand init` and `build` that must be
deterministic, not a shared file on disk doing the work. (The stock test kit `make_kit` builds in
tests/conftest.py is not used here: it saves a raw python-pptx Presentation() straight to a .pptx,
and python-pptx's zip writer stamps that file with the current time, so two independent calls to it
seconds apart are never byte-identical. That is a quirk of a test-only shortcut, not of the engine;
`brand init`'s own template.potx is stamped to a fixed date for exactly this reason.)
"""
from __future__ import annotations

import hashlib
import time
import zipfile
from pathlib import Path

from scn import brand_source, init_root, write_deck_md, write_hero

DECK = """
---
brand: stable-co
---

## Stable Co quarterly review
layout: title
subtitle: Shipments, margins and next quarter

## Paper volume grew 12% in Q3
layout: content

- Copy paper led the growth
- Card stock held flat

## 12%
layout: big-number
caption: Volume growth, Q2 to Q3

## Volume by product
layout: chart

```chart
type: column
categories: [Jul, Aug, Sep]
series:
  - name: Copy paper
    values: [410, 378, 331]
  - name: Card stock
    values: [120, 118, 121]
```

## Open items
layout: table

| Item | Owner | Due |
|---|---|---|
| Warehouse lease | Ops | Oct |

## The warehouse
layout: image

### image
![Warehouse](assets/hero.png)

### caption
The current site.

## Thank you
layout: closing
subtitle: ops@example.com
"""


def build_in_a_fresh_workspace(tmp_path: Path) -> Path:
    """An independent workspace: its own generated kit, its own deck, nothing shared on disk with
    any other workspace. Returns the built .pptx's path."""
    from deck_builder.cli import main

    root = init_root(tmp_path)
    src = brand_source(tmp_path, "stable-co", layout_set="full")
    assert main(["--config", str(root / "deck-builder.toml"), "brand", "init", "stable-co",
                "--from", str(src)]) == 0
    write_hero(root / "workspace" / "decks" / "stable")
    deck = write_deck_md(root, "stable/deck.md", DECK)
    code = main(["--config", str(root / "deck-builder.toml"), "build", str(deck), "-o", str(root / "out.pptx")])
    assert code == 0
    return root / "out.pptx"


def test_the_same_deck_built_in_two_unrelated_workspaces_is_byte_identical(tmp_path_factory):
    a = build_in_a_fresh_workspace(tmp_path_factory.mktemp("workspace-a"))
    time.sleep(2.1)  # past the zip timestamp's 2-second resolution, so a clock leak would show
    b = build_in_a_fresh_workspace(tmp_path_factory.mktemp("workspace-b"))
    assert a.read_bytes() == b.read_bytes()


def test_the_embedded_chart_workbook_is_also_byte_identical(tmp_path_factory):
    """The chart's data lives in an embedded .xlsx inside the .pptx; the whole-file comparison above
    already covers it, but this isolates that one part, since it is its own generated artifact (an
    openpyxl workbook with its own timestamp fields that must be stamped, not left to the clock)."""
    a = build_in_a_fresh_workspace(tmp_path_factory.mktemp("workspace-chart-a"))
    time.sleep(2.1)
    b = build_in_a_fresh_workspace(tmp_path_factory.mktemp("workspace-chart-b"))

    def embedded_workbooks(pptx):
        with zipfile.ZipFile(pptx) as z:
            names = sorted(n for n in z.namelist() if n.startswith("ppt/embeddings/") and n.endswith(".xlsx"))
            assert names, "expected at least one embedded chart workbook"
            return {n: hashlib.sha256(z.read(n)).hexdigest() for n in names}

    assert embedded_workbooks(a) == embedded_workbooks(b)
