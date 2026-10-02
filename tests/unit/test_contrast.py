"""LOW_CONTRAST: brand check measures color pairs with the WCAG 2.2 formula."""
from pathlib import Path

import pytest
import yaml

from conftest import cli_json
from deck_builder.brand.kit import contrast

DEMO = Path(__file__).resolve().parents[1] / "fixtures" / "demo-brands" / "brands"


@pytest.mark.parametrize("a, b, ratio", [
    ("000000", "FFFFFF", 21.0), ("FFFFFF", "000000", 21.0), ("777777", "777777", 1.0), ("767676", "FFFFFF", 4.54),
])
def test_contrast_ratio(a, b, ratio):
    assert contrast(a, b) == pytest.approx(ratio, abs=0.01)


def low(out):
    return [i for i in out["issues"] if i["code"] == "LOW_CONTRAST"]


def test_a_brand_with_readable_colors_passes(ws, capsys):
    code, out = cli_json(ws, "brand", "check", "stock", capsys=capsys)
    assert code == 0, out["issues"]
    assert low(out) == []


def test_a_light_link_color_warns_with_the_pair_ratio_and_minimum(ws, capsys):
    src = DEMO / "briarfield-paper" / "brand.yaml"
    code, out = cli_json(ws, "brand", "init", "briarfield-paper", "--from", str(src), capsys=capsys)
    assert code == 0  # a warning, not an error
    issues = low(out)
    assert {i["severity"] for i in issues} == {"warning"}
    link = next(i for i in issues if i["message"].startswith("hlink on lt1"))
    assert link["message"] == "hlink on lt1 (#C99455 on #FFFFFF) is 2.67:1; needs 4.5:1"
    assert (link["actual"], link["limit"]) == (2.67, 4.5)
    icon = next(i for i in issues if i["message"].startswith("icon color accent"))
    assert icon["limit"] == 3.0


def test_charts_without_token_colors_are_checked_on_the_theme_accents(ws, capsys):
    path = ws / "brands" / "stock" / "tokens.yaml"
    tokens = yaml.safe_load(path.read_text())
    del tokens["chart"]["colors"]
    path.write_text(yaml.safe_dump(tokens, sort_keys=False))
    code, out = cli_json(ws, "brand", "check", "stock", capsys=capsys)
    assert code == 0
    # python-pptx's stock theme: accent3 9BBB59, accent5 4BACC6 and accent6 F79646 are too light on white
    assert sorted(i["message"].split(" on ")[0] for i in low(out)) == [
        "chart color accent3", "chart color accent5", "chart color accent6"]
