"""Render tier: the showcase deck in the three demo brands renders with their real fonts and no flags.

The demo brands use Georgia, Arial, Avenir Next and Helvetica Neue, which ship with macOS, so the font
assertions only hold there.
"""
import json
import sys
from pathlib import Path

import pytest

from conftest import init_designed_demo_brands
from deck_builder.cli import main
from deck_builder.qa import tools

DEMO = Path(__file__).resolve().parents[1] / "fixtures" / "demo-brands"
SLUGS = ("dumbder-nifftlin", "cubicle-nine", "soap-club")

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
    for deck in ("showcase", "layouts"):
        assert main(["--config", cfg, "build", str(DEMO / deck / "deck.md"), "--data",
                     str(DEMO / deck / "brands.csv"), "--name", "{{brand}}.pptx", "-o", str(root / deck)]) == 0
    return cfg, root / "showcase"


@pytest.mark.parametrize("slug", SLUGS)
def test_showcase_renders_in_the_brand_fonts_with_no_flags(built, slug, capsys):
    cfg, out = built
    capsys.readouterr()
    code, res = run("--config", cfg, "render", str(out / f"{slug}.pptx"), capsys=capsys)
    assert code == 0, res["issues"]
    assert [i for i in res["issues"] if i["code"] == "MISSING_FONT"] == []
    assert res["flagged_slides"] == []


@pytest.fixture(scope="module")
def designed(tmp_path_factory):
    root = tmp_path_factory.mktemp("designed-render")
    cfg = str(root / "deck-builder.toml")
    assert main(["init", "--dir", str(root)]) == 0
    init_designed_demo_brands(root, DEMO / "brands", SLUGS)
    assert main(["--config", cfg, "build", str(DEMO / "designed" / "deck.md"), "--data",
                 str(DEMO / "designed" / "brands.csv"), "--name", "{{brand}}.pptx", "-o", str(root / "out")]) == 0
    return cfg, root / "out"


@pytest.mark.parametrize("slug", SLUGS)
def test_designed_layouts_render_with_no_flags(designed, slug, capsys):
    """The designed fixture: cards, process steps, bands, section labels, subtitles and logo slots."""
    cfg, out = designed
    capsys.readouterr()
    code, res = run("--config", cfg, "render", str(out / f"{slug}.pptx"), capsys=capsys)
    assert code == 0, res["issues"]
    assert res["flagged_slides"] == []


@pytest.mark.parametrize("slug", SLUGS)
def test_every_layout_renders_with_no_flags(built, slug, capsys):
    """The layouts fixture, every generated layout with realistic content, renders clean in each brand."""
    cfg, showcase = built
    capsys.readouterr()
    code, res = run("--config", cfg, "render", str(showcase.parent / "layouts" / f"{slug}.pptx"), capsys=capsys)
    assert code == 0, res["issues"]
    assert res["flagged_slides"] == []
