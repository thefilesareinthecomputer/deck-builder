"""Render tier: the showcase deck in the three demo brands renders with their real fonts and no flags.

The demo brands use Georgia, Arial, Avenir Next and Helvetica Neue, which ship with macOS, so the font
assertions only hold there.
"""
import json
import sys
from pathlib import Path

import pytest

from deck_builder.cli import main
from deck_builder.qa import tools

DEMO = Path(__file__).resolve().parents[1] / "fixtures" / "demo-brands"
SLUGS = ("briarfield-paper", "cubicle-nine", "afterhours-soap")

pytestmark = [
    pytest.mark.render,
    pytest.mark.skipif(tools.soffice() is None or bool(tools.poppler_missing()),
                       reason="needs LibreOffice and poppler"),
    pytest.mark.skipif(sys.platform != "darwin", reason="the demo brands' fonts ship with macOS"),
]


def run(*argv, capsys):
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("demo-render")
    cfg = str(root / "deck-builder.toml")
    assert main(["init", "--dir", str(root)]) == 0
    for slug in SLUGS:
        assert main(["--config", cfg, "brand", "init", slug, "--from", str(DEMO / "brands" / slug / "brand.yaml")]) == 0
    out = root / "showcase"
    assert main(["--config", cfg, "build", str(DEMO / "showcase" / "deck.md"), "--data",
                 str(DEMO / "showcase" / "brands.csv"), "--name", "{{brand}}.pptx", "-o", str(out)]) == 0
    return cfg, out


@pytest.mark.parametrize("slug", SLUGS)
def test_showcase_renders_in_the_brand_fonts_with_no_flags(built, slug, capsys):
    cfg, out = built
    capsys.readouterr()
    code, res = run("--config", cfg, "render", str(out / f"{slug}.pptx"), capsys=capsys)
    assert code == 0, res["issues"]
    assert [i for i in res["issues"] if i["code"] == "MISSING_FONT"] == []
    assert res["flagged_slides"] == []
