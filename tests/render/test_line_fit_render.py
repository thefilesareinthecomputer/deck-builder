"""Render tier: text that fits its box's lines renders without overflow even past its character budget, which is
why check makes that budget a warning there (validate._check_field)."""
import json
import sys
from pathlib import Path

import pytest
import yaml

from conftest import init_demo_brands
from deck_builder import validate
from deck_builder.cli import main
from deck_builder.qa import tools

DEMO = Path(__file__).resolve().parents[1] / "fixtures" / "demo-brands"
SLUGS = ("dumbder-nifftlin", "cubicle-nine", "soap-club")
SENTENCE = "We restock the tester shelf every Monday before the store opens, and we log what sold that week. "

pytestmark = [
    pytest.mark.render,
    pytest.mark.skipif(tools.soffice() is None or bool(tools.poppler_missing()),
                       reason="needs LibreOffice and poppler"),
    pytest.mark.skipif(sys.platform != "darwin", reason="the demo brands' fonts ship with macOS"),
]


def _filled(fs: dict, gap: float) -> str:
    """As many words as the box's lines hold (less a bullet's gap), which is past its character budget."""
    text = ""
    for word in (SENTENCE * 40).split():
        longer = f"{text} {word}".strip()
        if validate._wrapped(longer, int(fs["line_chars"])) + gap > fs["max_lines"]:
            break
        text = longer
    assert len(text) > fs["max_chars"], "the test text has to be past the character budget"
    return text


@pytest.mark.parametrize("slug", SLUGS)
def test_text_that_fits_its_lines_renders_without_overflow(tmp_path, capsys, slug):
    assert main(["init", "--dir", str(tmp_path)]) == 0
    init_demo_brands(tmp_path, DEMO / "brands", (slug,))
    layouts = yaml.safe_load(next(tmp_path.rglob(f"{slug}/tokens.yaml")).read_text())["layouts"]
    gap = validate.BULLET_GAP_LINES
    deck = tmp_path / "decks" / "fit" / "deck.md"
    deck.parent.mkdir(parents=True)
    deck.write_text(f"---\nbrand: {slug}\n---\n"
                    f"## The tester shelf is full every Monday\nlayout: content\n\n"
                    f"{_filled(layouts['content']['fields']['body'], gap)}\n\n"
                    f"## Both stores restock the same way\nlayout: two-col\n\n### left\n"
                    f"{_filled(layouts['two-col']['fields']['left'], gap)}\n\n### right\n- One short point\n",
                    encoding="utf-8")
    capsys.readouterr()
    code = main(["--config", str(tmp_path / "deck-builder.toml"), "check", str(deck), "--render", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0, out["issues"]
    budget = {(i["code"], i["severity"]) for i in out["issues"] if i["code"].startswith("BUDGET_")}
    assert budget == {("BUDGET_CHARS", "warning")}
    assert not [i for i in out["issues"] if i["code"] == "OVERFLOW_MEASURED"]
    assert {c for f in out["flagged_slides"] for c in f["codes"]} <= {"BUDGET_CHARS", "WORDS_MANY"}
