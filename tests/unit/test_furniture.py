"""Slide numbers and footers: generated kits, built slides, adopted templates. Restraint is the bar."""
import shutil
from pathlib import Path

import pytest
import yaml
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.util import Emu

from conftest import cli_json
from deck_builder import template as tpl

DEMO = Path(__file__).resolve().parents[1] / "fixtures" / "demo-brands" / "brands"
EMU = 914400
HIDES_MASTER = {"Title", "Section", "Closing"}


def init_brand(ws, capsys, slug="briarfield-paper", **generate):
    src = ws / "src" / slug
    shutil.copytree(DEMO / slug, src, dirs_exist_ok=True)  # assets resolve beside the brand.yaml
    if generate:
        meta = yaml.safe_load((src / "brand.yaml").read_text())
        meta["generate"] = {**(meta.get("generate") or {}), **generate}
        (src / "brand.yaml").write_text(yaml.safe_dump(meta, sort_keys=False))
    code, out = cli_json(ws, "brand", "init", slug, "--from", str(src / "brand.yaml"), capsys=capsys)
    assert code == 0, out["issues"]
    return ws / "brands" / slug


def furniture(shapes) -> dict[str, object]:
    return {ph.placeholder_format.type.name: ph for ph in shapes
            if ph.placeholder_format.type in (PP_PLACEHOLDER.SLIDE_NUMBER, PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.DATE)}


# ---------------------------------------------------------------- generated kits


def test_the_master_has_a_quiet_number_and_footer_and_no_date(ws, capsys):
    kit = init_brand(ws, capsys)
    prs = tpl.open_template(kit / "template.potx")
    master = furniture(prs.slide_masters[0].placeholders)
    assert set(master) == {"SLIDE_NUMBER", "FOOTER"}
    num, ftr = master["SLIDE_NUMBER"], master["FOOTER"]
    h = prs.slide_height
    assert num.left == round(0.6 * EMU)  # left-aligned at the margin
    assert abs((num.top + num.height / 2) - (h - Emu(round(0.46 * EMU)))) < EMU * 0.01  # on the logo's line
    assert ftr.top == num.top and ftr.left == num.left + num.width  # same baseline, after the number
    for ph in (num, ftr):
        lvl = ph.text_frame._txBody.find(".//{*}lstStyle/{*}lvl1pPr")
        assert lvl.get("algn") == "l" and lvl.find("{*}buNone") is not None
        rpr = lvl.find("{*}defRPr")
        assert (rpr.get("sz"), rpr.get("b")) == ("1000", "0")
        assert rpr.find("{*}solidFill/{*}srgbClr").get("val") == "6A7971"  # briarfield's muted, 4.58:1
        assert ph._element.find("{*}spPr/{*}ln") is None and ph._element.find("{*}spPr/{*}solidFill") is None


def test_only_layouts_that_show_the_master_get_furniture(ws, capsys):
    prs = tpl.open_template(init_brand(ws, capsys) / "template.potx")
    for layout in prs.slide_masters[0].slide_layouts:
        got = set(furniture(layout.placeholders))
        assert got == (set() if layout.name in HIDES_MASTER else {"SLIDE_NUMBER", "FOOTER"}), layout.name


def test_tokens_record_the_furniture_color_choice(ws, capsys):
    tokens = yaml.safe_load((init_brand(ws, capsys) / "tokens.yaml").read_text())
    assert tokens["furniture"] == {"slide_numbers": True, "color": "muted"}


def test_a_muted_color_under_4_5_to_1_falls_back_to_ink(ws, capsys):
    kit = init_brand(ws, capsys, slug="afterhours-soap")  # muted 8D8180 is 3.76:1 on white
    assert yaml.safe_load((kit / "tokens.yaml").read_text())["furniture"]["color"] == "ink"
    num = furniture(tpl.open_template(kit / "template.potx").slide_masters[0].placeholders)["SLIDE_NUMBER"]
    assert num.text_frame._txBody.find(".//{*}defRPr/{*}solidFill/{*}srgbClr").get("val") == "211F24"


def test_the_brand_can_turn_slide_numbers_off(ws, capsys):
    kit = init_brand(ws, capsys, slide_numbers=False)
    prs = tpl.open_template(kit / "template.potx")
    master = furniture(prs.slide_masters[0].placeholders)
    assert set(master) == {"FOOTER"} and master["FOOTER"].left == round(0.6 * EMU)
    assert all("SLIDE_NUMBER" not in furniture(lay.placeholders) for lay in prs.slide_masters[0].slide_layouts)
    assert yaml.safe_load((kit / "tokens.yaml").read_text())["furniture"]["slide_numbers"] is False


@pytest.mark.parametrize("slug", ["briarfield-paper"])
def test_generation_stays_deterministic(ws, capsys, slug):
    first = (init_brand(ws, capsys, slug) / "template.potx").read_bytes()
    code, out = cli_json(ws, "brand", "init", slug, "--from", str(ws / "src" / slug / "brand.yaml"), "--force",
                         capsys=capsys)
    assert code == 0
    assert (ws / "brands" / slug / "template.potx").read_bytes() == first
