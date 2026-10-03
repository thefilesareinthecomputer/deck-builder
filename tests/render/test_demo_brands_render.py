"""Render tier: every demo-brand fixture deck renders in its brands with their real fonts and no flags.

The demo brands use Georgia, Arial, Avenir Next and Helvetica Neue, which ship with macOS, so the font
assertions only hold there.
"""
import json
import sys
from pathlib import Path

import pytest

from conftest import ALL_OPTIONS, DESIGNED_DEFAULTS, FULL_SET, init_demo_brands
from deck_builder.cli import main
from deck_builder.qa import tools

DEMO = Path(__file__).resolve().parents[1] / "fixtures" / "demo-brands"
SLUGS = ("dumbder-nifftlin", "cubicle-nine", "soap-club")
DECKS = sorted((p.parent.parent.name, p.parent.name) for p in (DEMO / "decks").glob("*/*/deck.md"))

pytestmark = [
    pytest.mark.render,
    pytest.mark.skipif(tools.soffice() is None or bool(tools.poppler_missing()),
                       reason="needs LibreOffice and poppler"),
    pytest.mark.skipif(sys.platform != "darwin", reason="the demo brands' fonts ship with macOS"),
]


def run(*argv, capsys):
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def kits(tmp_path_factory, name: str, generate: dict | None = None) -> tuple[str, Path]:
    """A workspace with the three demo brands, from their own brand.yaml or with these generate settings."""
    root = tmp_path_factory.mktemp(name)
    assert main(["init", "--dir", str(root)]) == 0
    init_demo_brands(root, DEMO / "brands", SLUGS, generate)
    return str(root / "deck-builder.toml"), root / "out"


def bulk(cfg: str, out: Path, name: str) -> None:
    assert main(["--config", cfg, "build", str(DEMO / name / "deck.md"), "--data", str(DEMO / name / "brands.csv"),
                 "--name", "{{brand}}.pptx", "-o", str(out / name)]) == 0, name


def rendered_clean(cfg: str, pptx: Path, capsys) -> dict:
    capsys.readouterr()
    code, res = run("--config", cfg, "render", str(pptx), capsys=capsys)
    assert code == 0, res["issues"]
    assert res["flagged_slides"] == []
    return res


@pytest.fixture(scope="module")
def own_kits(tmp_path_factory):
    """Each brand's own kit: the showcase (the README's deck) and the nine brand decks."""
    cfg, out = kits(tmp_path_factory, "own-kits")
    bulk(cfg, out, "showcase")
    bulk(cfg, out, "code")
    for slug, name in DECKS:
        assert main(["--config", cfg, "build", str(DEMO / "decks" / slug / name / "deck.md"), "-o",
                     str(out / "decks" / f"{slug}-{name}.pptx")]) == 0, (slug, name)
    return cfg, out


@pytest.fixture(scope="module", params=[("layouts", FULL_SET), ("designed", DESIGNED_DEFAULTS),
                                        ("options", ALL_OPTIONS)], ids=["layouts", "designed", "options"])
def overridden(request, tmp_path_factory):
    """Fixtures written for one kit configuration across all three brands: every full-set layout, every
    designed-set layout on its defaults, and every designed-set option switched on."""
    name, generate = request.param
    cfg, out = kits(tmp_path_factory, f"{name}-kits", generate)
    bulk(cfg, out, name)
    return cfg, out / name


@pytest.mark.parametrize("slug", SLUGS)
def test_showcase_renders_in_the_brand_fonts_with_no_flags(own_kits, slug, capsys):
    cfg, out = own_kits
    res = rendered_clean(cfg, out / "showcase" / f"{slug}.pptx", capsys)
    assert [i for i in res["issues"] if i["code"] == "MISSING_FONT"] == []


@pytest.mark.parametrize("slug", SLUGS)
def test_code_deck_renders_in_the_code_font_with_no_flags(own_kits, slug, capsys):
    """No line of code runs past its panel (OVERFLOW_MEASURED reads each code token as pdftotext splits it),
    and the code renders in Menlo, which ships with macOS."""
    from deck_builder.qa.fonts import embedded

    cfg, out = own_kits
    res = rendered_clean(cfg, out / "code" / f"{slug}.pptx", capsys)
    assert any(f.startswith("menlo") for f in embedded(Path(res["render_dir"]) / "deck.pdf"))


@pytest.mark.parametrize("slug,name", DECKS)
def test_each_brand_deck_renders_with_no_flags(own_kits, slug, name, capsys):
    cfg, out = own_kits
    rendered_clean(cfg, out / "decks" / f"{slug}-{name}.pptx", capsys)


@pytest.mark.parametrize("slug", SLUGS)
def test_every_layout_and_option_renders_with_no_flags(overridden, slug, capsys):
    cfg, out = overridden
    rendered_clean(cfg, out / f"{slug}.pptx", capsys)
