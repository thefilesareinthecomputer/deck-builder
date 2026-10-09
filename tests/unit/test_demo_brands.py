"""The demo-brands fixtures: decks bulk-built and built one by one into the three generated brands."""
import re
from pathlib import Path

import pytest

from conftest import ALL_OPTIONS, DESIGNED_DEFAULTS, FULL_SET, cli_json, init_demo_brands, stage_images_deck

DEMO = Path(__file__).resolve().parents[1] / "fixtures" / "demo-brands"
SLUGS = ("dumbder-nifftlin", "cubicle-nine", "soap-club")
DECKS = sorted((p.parent.parent.name, p.parent.name) for p in (DEMO / "decks").glob("*/*/deck.md"))


def workspace(tmp_path_factory, name: str, generate: dict | None = None) -> Path:
    from deck_builder.cli import main

    root = tmp_path_factory.mktemp(name)
    assert main(["init", "--dir", str(root)]) == 0
    init_demo_brands(root, DEMO / "brands", SLUGS, generate)
    return root


@pytest.fixture(scope="module")
def demo_ws(tmp_path_factory):
    """Each demo brand from its own brand.yaml: the kits the showcase and the brand decks are written for."""
    return workspace(tmp_path_factory, "demo")


def bulk(ws: Path, name: str, capsys: pytest.CaptureFixture[str]) -> dict:
    capsys.readouterr()
    code, out = cli_json(ws, "build", str(DEMO / name / "deck.md"), "--data", str(DEMO / name / "brands.csv"),
                         "--name", "{{brand}}.pptx", "-o", str(ws / name), capsys=capsys)
    assert code == 0, out["issues"]
    assert [i for i in out["issues"] if i["severity"] == "error"] == []
    return out


def test_showcase_builds_clean_in_all_three_brands(demo_ws, capsys):
    """The README's deck: the designed set's cards, chart header, bands and logo row in each brand's kit."""
    out = bulk(demo_ws, "showcase", capsys)
    assert out["issues"] == []
    assert sorted(Path(o["output"]).name for o in out["outputs"]) == sorted(f"{s}.pptx" for s in SLUGS)


def test_code_deck_builds_clean_in_all_three_brands(demo_ws, capsys):
    """Python, SQL, YAML, bash and a markdown block holding its own fence, with highlighted lines, line numbers,
    a filename and code-right, in a dark-theme kit (Dumbder Nifftlin), a read kit (Cubicle 9) and a light
    projected kit (Soap Club)."""
    out = bulk(demo_ws, "code", capsys)
    assert out["issues"] == []
    text = (DEMO / "code" / "deck.md").read_text()
    for case in ("```python {4-5} lines title=", "```sql {7}", "```yaml lines", "```bash", "````markdown",
                 "layout: code-right"):
        assert case in text


@pytest.mark.parametrize("brand", ["dumbder-nifftlin", "neutral"])
def test_the_readme_example_checks_clean_on_its_brand_and_on_neutral(demo_ws, brand, capsys):
    """The README's deck.md example, whose chart slide is its brands image, and what it tells a reader to try
    on the neutral brand that `init` creates."""
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text()
    example = re.search(r"````markdown\n(.*?)````", readme, re.S)
    assert example
    deck = demo_ws / "readme" / "deck.md"
    deck.parent.mkdir(exist_ok=True)
    deck.write_text(example.group(1).replace("brand: dumbder-nifftlin", f"brand: {brand}"))
    capsys.readouterr()
    code, out = cli_json(demo_ws, "check", str(deck), capsys=capsys)
    assert code == 0 and out["issues"] == [], out["issues"]


def test_layouts_deck_uses_every_full_set_layout_and_builds_clean_in_all_three_brands(tmp_path_factory, capsys):
    """The layouts fixture puts every full-set layout but team on a slide, including the cases that
    used to look unfinished: a short bullet list, a short table, a comparison and a two-column slide."""
    from pptx import Presentation

    used = set(re.findall(r"(?m)^layout: (\S+)$", (DEMO / "layouts" / "deck.md").read_text()))
    assert used == {"title", "section", "agenda", "content", "two-col", "comparison", "big-number", "statement",
                    "chart", "table", "image", "image-full", "image-right", "image-2", "icon-row", "quote",
                    "closing"}  # code and code-right: demo-brands/code
    ws = workspace(tmp_path_factory, "full", FULL_SET)
    bulk(ws, "layouts", capsys)
    dark = Presentation(str(ws / "layouts" / "soap-club.pptx")).slides[5].slide_layout
    assert dark.name == "Big Number" and dark._element.get("showMasterSp") == "0"  # big_number: dark


def test_designed_deck_uses_the_new_layouts_and_builds_clean_in_all_three_brands(tmp_path_factory, capsys):
    """The designed fixture puts cards, process steps, bands, section labels, subtitles and logos on
    slides with realistic content; the vendor logos are transparent PNGs, fitted rather than cropped."""
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    text = (DEMO / "designed" / "deck.md").read_text()
    assert {"cards-3", "cards-4", "process-4", "process-5", "bands-3"} <= set(re.findall(r"(?m)^layout: (\S+)$", text))
    ws = workspace(tmp_path_factory, "designed", DESIGNED_DEFAULTS)
    bulk(ws, "designed", capsys)
    prs = Presentation(str(ws / "designed" / "cubicle-nine.pptx"))
    logos = [sh for slide in prs.slides for sh in slide.shapes if sh.shape_type == MSO_SHAPE_TYPE.PICTURE
             and sh._element.nvPicPr.cNvPr.get("descr", "").endswith(" logo")]
    assert len(logos) == 3  # two on the comparison panels, one in image-right
    iw, ih = 1600, 368  # every demo logo's canvas; its art sits left of center with transparent margins
    for pic in logos:  # only the transparent margin is cropped, so the art keeps its own proportions
        assert pic.crop_right > 0.1
        shown = ((1 - pic.crop_left - pic.crop_right) * iw) / ((1 - pic.crop_top - pic.crop_bottom) * ih)
        assert abs(pic.width / pic.height - shown) < 0.02


def test_every_brand_has_a_pitch_a_review_and_an_edge_deck():
    assert [(slug, name) for slug in sorted(SLUGS) for name in ("edge", "pitch", "review")] == DECKS


@pytest.mark.parametrize("slug", SLUGS)
def test_images_deck_shows_screenshots_whole_and_says_where_each_image_lands(demo_ws, slug, capsys):
    """demo-brands/images/: a wide and a tall screenshot on image-right, two on image-2, a capture the process
    slide can't show, and a photo, on each brand's designed kit."""
    import json

    deck = stage_images_deck(demo_ws / "decks" / f"images-{slug}", slug)
    capsys.readouterr()
    code, out = cli_json(demo_ws, "build", str(deck), "-o", str(demo_ws / "out" / f"images-{slug}.pptx"),
                         capsys=capsys)
    assert code == 0, out["issues"]
    assert [(i["code"], i["slide"]) for i in out["issues"]] == [("IMAGE_NO_SLOT", 4)], out["issues"]
    assert "image-right (image)" in out["issues"][0]["message"]
    slides = json.loads(Path(out["manifest"]).read_text(encoding="utf-8"))["slides"]
    fits = [{k: f.get("fit") for k, f in s["fields"].items() if "asset" in f} for s in slides]
    assert fits == [{"image": "contain"}, {"image": "contain"}, {"image1": "contain", "image2": "contain"}, {},
                    {"image": None}]
    code, out = cli_json(demo_ws, "assets", str(deck), "--images", capsys=capsys)
    assert code == 0, out
    rows = [(r["slide"], r["where"], Path(r["path"]).name, r["status"], r.get("sides"), r.get("missing"))
            for r in out["images"]]
    assert rows == [(1, "image", "contact-sheet.png", "shown", None, None),
                    (2, "image", "order-form.png", "shown", None, None),
                    (3, "image1", "showcase.png", "shown", None, None),
                    (3, "image2", "contact-sheet.png", "shown", None, None),
                    (4, "notes", "retry-log.png", "notes only", None, True),
                    (5, "image", "photo.png", "cropped", "left and right", None),
                    (None, None, "spare.png", "unused", None, None)]


@pytest.mark.parametrize("slug,name", DECKS)
def test_each_brand_deck_checks_and_builds_clean(demo_ws, slug, name, capsys):
    """Nine decks, three per brand, each written for its brand's kit: errors fail, and only the edge
    decks may carry convention warnings, on the slides written to trigger them."""
    deck = DEMO / "decks" / slug / name / "deck.md"
    capsys.readouterr()
    code, out = cli_json(demo_ws, "build", str(deck), "-o", str(demo_ws / "out" / f"{slug}-{name}.pptx"),
                         capsys=capsys)
    assert code == 0, out
    assert [i for i in out["issues"] if i["severity"] == "error"] == []
    if name != "edge":
        assert out["issues"] == [], out["issues"]


def test_options_deck_builds_clean_with_every_designed_option_in_all_three_brands(tmp_path_factory, capsys):
    """The options fixture: quote takeaways, circle icon tiles, process icons (some from the starter
    set), rectangle band labels, bold keywords, the logo row, a deck-wide kicker and first_slide_number."""
    bulk(workspace(tmp_path_factory, "options", ALL_OPTIONS), "options", capsys)
