"""Cost of output: agents read a step's --json, so it has to stay compact and never echo the deck
back. These budgets are generous (room for longer tmp-dir paths on another machine) but still tight
enough that a regression which starts dumping slide content into --json would blow past them.
"""
from __future__ import annotations

import json

from scn import json_bytes, setup_cycle_decks

from conftest import cli_json

SENTINEL = "SENTINEL-9f3b2a7e-this-exact-run-of-text-must-never-appear-in-any-json-output-below"

# Actual sizes measured against this suite (see the worker's report): a 40-slide check/build/render
# payload runs 500-1600 bytes total, regardless of slide count, because only flagged slides and
# counts are reported. 300 bytes/slide leaves roughly 10x headroom before this would catch anything
# but a real regression.
PER_SLIDE_BUDGET = 300


def test_the_40_slide_decks_json_never_grows_with_slide_count(tmp_path, capsys):
    root, deck3, deck40 = setup_cycle_decks(tmp_path, sentinel=SENTINEL)
    capsys.readouterr()

    code, check3 = cli_json(root, "check", str(deck3), capsys=capsys)
    assert code == 0, check3["issues"]
    code, check40 = cli_json(root, "check", str(deck40), capsys=capsys)
    assert code == 0, check40["issues"]

    code, build3 = cli_json(root, "build", str(deck3), capsys=capsys)
    assert code == 0, build3["issues"]
    code, build40 = cli_json(root, "build", str(deck40), capsys=capsys)
    assert code == 0, build40["issues"]

    code, render40 = cli_json(root, "check", str(deck40), "--render", capsys=capsys)
    assert code == 0, [i for i in render40["issues"] if i["severity"] == "error"]
    assert render40["flagged_slides"] == []

    # the whole point: a 40-slide deck's --json is not meaningfully bigger than a 3-slide deck's
    assert json_bytes(check40) < 40 * PER_SLIDE_BUDGET
    assert json_bytes(build40) < 40 * PER_SLIDE_BUDGET
    assert json_bytes(render40) < 40 * PER_SLIDE_BUDGET
    assert json_bytes(check40) < json_bytes(check3) * 5  # not scaling with slide count
    assert json_bytes(build40) < json_bytes(build3) * 5

    # no step echoes the slide body the agent sent: the sentinel never comes back
    for step in (check3, check40, build3, build40, render40):
        blob = json.dumps(step)
        assert SENTINEL not in blob
        # nor does any step dump a slide's own field map (that's manifest.json's job, not --json's)
        assert '"fields"' not in blob


def test_a_tiny_decks_json_also_stays_small(tmp_path, capsys):
    """A regression that bloats --json shows up on a small deck too, not only at 40 slides."""
    root, deck3, _ = setup_cycle_decks(tmp_path, slug="northfield-tiny")
    capsys.readouterr()
    code, out = cli_json(root, "check", str(deck3), capsys=capsys)
    assert code == 0, out["issues"]
    assert json_bytes(out) < 1500
    code, out = cli_json(root, "build", str(deck3), capsys=capsys)
    assert code == 0, out["issues"]
    assert json_bytes(out) < 1500
