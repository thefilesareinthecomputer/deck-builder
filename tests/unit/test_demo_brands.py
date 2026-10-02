"""The demo-brands fixtures: one showcase deck bulk-builds into three generated brands."""
from pathlib import Path

import pytest

from conftest import ALL_OPTIONS, BRAND_KITS, cli_json, init_designed_demo_brands

DEMO = Path(__file__).resolve().parents[1] / "fixtures" / "demo-brands"
SLUGS = ("dumbder-nifftlin", "cubicle-nine", "soap-club")


@pytest.fixture(scope="module")
def demo_ws(tmp_path_factory):
    from deck_builder.cli import main

    root = tmp_path_factory.mktemp("demo")
    assert main(["init", "--dir", str(root)]) == 0
    for slug in SLUGS:
        args = ["--config", str(root / "deck-builder.toml"), "brand", "init", slug,
                "--from", str(DEMO / "brands" / slug / "brand.yaml")]
        assert main(args) == 0, slug
    return root


def test_showcase_builds_clean_in_all_three_brands(demo_ws, capsys):
    capsys.readouterr()
    code, out = cli_json(demo_ws, "build", str(DEMO / "showcase" / "deck.md"),
                         "--data", str(DEMO / "showcase" / "brands.csv"), "--name", "{{brand}}.pptx",
                         "-o", str(demo_ws / "showcase"), capsys=capsys)
    assert code == 0, out["issues"]
    assert [i for i in out["issues"] if i["severity"] == "error"] == []
    assert sorted(Path(o["output"]).name for o in out["outputs"]) == sorted(f"{s}.pptx" for s in SLUGS)


def test_layouts_deck_uses_every_layout_and_builds_clean_in_all_three_brands(demo_ws, capsys):
    """The layouts fixture puts every generated layout but team on a slide, including the cases that
    used to look unfinished: a short bullet list, a short table, a comparison and a two-column slide."""
    import re

    from pptx import Presentation

    text = (DEMO / "layouts" / "deck.md").read_text()
    used = set(re.findall(r"(?m)^layout: (\S+)$", text))
    assert used == {"title", "section", "agenda", "content", "two-col", "comparison", "big-number", "chart",
                    "table", "image", "image-right", "icon-row", "quote", "closing"}
    capsys.readouterr()
    code, out = cli_json(demo_ws, "build", str(DEMO / "layouts" / "deck.md"),
                         "--data", str(DEMO / "layouts" / "brands.csv"), "--name", "{{brand}}.pptx",
                         "-o", str(demo_ws / "layouts"), capsys=capsys)
    assert code == 0, out["issues"]
    assert [i for i in out["issues"] if i["severity"] == "error"] == []
    dark = Presentation(str(demo_ws / "layouts" / "soap-club.pptx")).slides[5].slide_layout
    assert dark.name == "Big Number" and dark._element.get("showMasterSp") == "0"  # big_number: dark


@pytest.fixture(scope="module")
def designed_ws(tmp_path_factory):
    from deck_builder.cli import main

    root = tmp_path_factory.mktemp("designed")
    assert main(["init", "--dir", str(root)]) == 0
    init_designed_demo_brands(root, DEMO / "brands", SLUGS)
    return root


def test_designed_deck_uses_the_new_layouts_and_builds_clean_in_all_three_brands(designed_ws, capsys):
    """The designed fixture puts cards, process steps, bands, section labels, subtitles and logos on
    slides with realistic content; the vendor logos are transparent PNGs, fitted rather than cropped."""
    import re

    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    text = (DEMO / "designed" / "deck.md").read_text()
    assert {"cards-3", "cards-4", "process-4", "process-5", "bands-3"} <= set(re.findall(r"(?m)^layout: (\S+)$", text))
    capsys.readouterr()
    code, out = cli_json(designed_ws, "build", str(DEMO / "designed" / "deck.md"),
                         "--data", str(DEMO / "designed" / "brands.csv"), "--name", "{{brand}}.pptx",
                         "-o", str(designed_ws / "designed"), capsys=capsys)
    assert code == 0, out["issues"]
    assert [i for i in out["issues"] if i["severity"] == "error"] == []
    prs = Presentation(str(designed_ws / "designed" / "cubicle-nine.pptx"))
    logos = [sh for slide in prs.slides for sh in slide.shapes if sh.shape_type == MSO_SHAPE_TYPE.PICTURE
             and sh._element.nvPicPr.cNvPr.get("descr", "").endswith(" logo")]
    assert len(logos) == 3  # two on the comparison panels, one in image-right
    iw, ih = 1600, 368  # every demo logo's canvas; its art sits left of center with transparent margins
    for pic in logos:  # only the transparent margin is cropped, so the art keeps its own proportions
        assert pic.crop_right > 0.1
        shown = ((1 - pic.crop_left - pic.crop_right) * iw) / ((1 - pic.crop_top - pic.crop_bottom) * ih)
        assert abs(pic.width / pic.height - shown) < 0.02


DECKS = sorted((p.parent.parent.name, p.parent.name) for p in (DEMO / "decks").glob("*/*/deck.md"))


@pytest.fixture(scope="module")
def brand_kits(tmp_path_factory):
    """Each demo brand generated with its own designed-set options (BRAND_KITS), in one workspace."""
    from deck_builder.cli import main

    root = tmp_path_factory.mktemp("brand-kits")
    assert main(["init", "--dir", str(root)]) == 0
    for slug, options in BRAND_KITS.items():
        init_designed_demo_brands(root, DEMO / "brands", (slug,), options)
    return root


def test_every_brand_has_a_pitch_a_review_and_an_edge_deck():
    assert [(slug, name) for slug in sorted(BRAND_KITS) for name in ("edge", "pitch", "review")] == DECKS


@pytest.mark.parametrize("slug,name", DECKS)
def test_each_brand_deck_checks_and_builds_clean(brand_kits, slug, name, capsys):
    """Nine decks, three per brand, each written for its brand's kit: errors fail, and only the edge
    decks may carry convention warnings, on the slides written to trigger them."""
    deck = DEMO / "decks" / slug / name / "deck.md"
    capsys.readouterr()
    code, out = cli_json(brand_kits, "build", str(deck), "-o", str(brand_kits / "out" / f"{slug}-{name}.pptx"),
                         capsys=capsys)
    assert code == 0, out
    assert [i for i in out["issues"] if i["severity"] == "error"] == []
    if name != "edge":
        assert out["issues"] == [], out["issues"]


def test_options_deck_builds_clean_with_every_designed_option_in_all_three_brands(tmp_path, capsys):
    """The options fixture: quote takeaways, circle icon tiles, process icons (some from the starter
    set), rectangle band labels, bold keywords, the logo row, a deck-wide kicker and first_slide_number."""
    from deck_builder.cli import main

    assert main(["init", "--dir", str(tmp_path)]) == 0
    init_designed_demo_brands(tmp_path, DEMO / "brands", SLUGS, ALL_OPTIONS)
    if not (Path(__file__).resolve().parents[2] / "src" / "deck_builder" / "data" / "icons" / "database.png").is_file():
        pytest.skip("run scripts/make_starter_icons.py to draw the full starter set")
    capsys.readouterr()
    code, out = cli_json(tmp_path, "build", str(DEMO / "options" / "deck.md"),
                         "--data", str(DEMO / "options" / "brands.csv"), "--name", "{{brand}}.pptx",
                         "-o", str(tmp_path / "options"), capsys=capsys)
    assert code == 0, out["issues"]
    assert [i for i in out["issues"] if i["severity"] == "error"] == []
