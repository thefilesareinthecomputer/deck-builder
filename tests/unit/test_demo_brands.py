"""The demo-brands fixtures: one showcase deck bulk-builds into three generated brands."""
from pathlib import Path

import pytest

from conftest import cli_json, init_designed_demo_brands

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
    for pic in logos:
        assert (pic.crop_left, pic.crop_right, pic.crop_top, pic.crop_bottom) == (0, 0, 0, 0)
        assert abs(pic.width / pic.height - 1600 / 368) < 0.01
