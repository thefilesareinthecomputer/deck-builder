import hashlib

import pytest
import yaml
from PIL import Image
from pptx import Presentation

from conftest import cli_json, write_deck
from deck_builder.template import open_template

BRAND = {
    "spec_version": 1,
    "name": "Pemberton Paper Co.",
    "slug": "pemberton",
    "version": "1.0.0",
    "palette": {"primary": "1F3A5F", "accent": "E07A2F", "ink": "1B1B1B", "muted": "6B7280",
                "surface": "F4F5F7", "background": "FFFFFF"},
    "fonts": {"heading": {"family": "Georgia", "fallback": "Times New Roman"},
              "body": {"family": "Arial", "fallback": "Liberation Sans"}},
    "logos": {"primary": "assets/logo.png"},
    "icons": {"dir": "assets/icons", "default_color": "accent", "source": "made for tests"},
    "lint": {"max_slides": 40, "banned_patterns": []},
    "generate": {"slide_size": "16:9", "layout_set": "standard", "logo_on_master": "primary"},
}


def source(tmp_path, **gen):
    src = tmp_path / "src"
    (src / "assets" / "icons").mkdir(parents=True)
    Image.new("RGB", (600, 200), "#1F3A5F").save(src / "assets" / "logo.png")
    Image.new("RGBA", (256, 256), (0, 0, 0, 255)).save(src / "assets" / "icons" / "truck.png")
    meta = {**BRAND, "generate": {**BRAND["generate"], **gen}}
    (src / "brand.yaml").write_text(yaml.safe_dump(meta, sort_keys=False))
    return src / "brand.yaml"


@pytest.mark.parametrize("layout_set", ["minimal", "standard", "full"])
def test_generated_kit_passes_brand_check(ws, capsys, tmp_path, layout_set):
    src = source(tmp_path, layout_set=layout_set)
    code, out = cli_json(ws, "brand", "init", "pemberton", "--from", str(src), capsys=capsys)
    assert code == 0, out["issues"]
    code, out = cli_json(ws, "brand", "check", "pemberton", capsys=capsys)
    assert code == 0, out["issues"]


def test_template_is_16_9_with_named_layouts_theme_and_logo(ws, capsys, tmp_path):
    cli_json(ws, "brand", "init", "pemberton", "--from", str(source(tmp_path)), capsys=capsys)
    kit = ws / "brands" / "pemberton"
    prs = open_template(kit / "template.potx")
    assert (prs.slide_width, prs.slide_height) == (12192000, 6858000)
    names = [lay.name for lay in prs.slide_layouts]
    assert names == ["Title", "Section", "Content", "Two Column", "Big Number", "Chart", "Table", "Image",
                     "Quote", "Closing"]
    from deck_builder.brand.inspect import theme

    th = theme(kit / "template.potx")
    assert th["colors"]["dk2"] == "1F3A5F" and th["colors"]["accent2"] == "E07A2F"
    assert th["fonts"] == {"heading": "Georgia", "body": "Arial"}
    master_pics = [s for s in prs.slide_masters[0].shapes if s.shape_type == 13]
    assert len(master_pics) == 1
    assert (kit / "assets" / "icons" / "truck.png").is_file()


def test_generation_is_deterministic(ws, capsys, tmp_path):
    src = source(tmp_path)
    cli_json(ws, "brand", "init", "pemberton", "--from", str(src), capsys=capsys)
    kit = ws / "brands" / "pemberton"
    first = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (kit / "template.potx", kit / "tokens.yaml")}
    cli_json(ws, "brand", "init", "pemberton", "--from", str(src), "--force", capsys=capsys)
    again = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (kit / "template.potx", kit / "tokens.yaml")}
    assert first == again


def test_generated_kit_builds_every_layout(ws, capsys, tmp_path):
    cli_json(ws, "brand", "init", "pemberton", "--from", str(source(tmp_path, layout_set="full")), capsys=capsys)
    deck = write_deck(ws, """
    ---
    brand: pemberton
    ---

    ## Pemberton Paper review
    layout: title
    subtitle: Q3 shipments

    ## Agenda
    layout: agenda

    - Volume
    - Margins

    ## Volume
    layout: section
    kicker: Part 1

    ## Copy paper led growth
    layout: content

    - Two new accounts

    ## Before and after
    layout: two-col

    ### left
    - Manual counts

    ### right
    - Scanned counts

    ## Options
    layout: comparison
    left-heading: Lease
    right-heading: Buy

    ### left
    - Lower upfront

    ### right
    - Lower total

    ## 12%
    layout: big-number
    caption: Volume growth

    ## By month
    layout: chart

    ```chart
    categories: [Jul, Aug]
    series: [{name: Copy, values: [1, 2]}]
    ```

    ## Open items
    layout: table

    | Item | Owner |
    |---|---|
    | Lease | Ops |

    ## Warehouse
    layout: image

    ### image
    ![Logo](brand:logo/primary)

    ### caption
    The main site.

    ## Routes
    layout: image-right

    - North route

    ### image
    ![Logo](brand:logo/primary)

    ## How we ship
    layout: icon-row
    icon1: brand:icon/truck
    text1: Daily trucks

    ## Team
    layout: team
    name1: Ops lead

    ## "Paper is still the fastest way to sign a deal."
    layout: quote
    attribution: A regional buyer

    ## Thank you
    layout: closing
    subtitle: ops@example.com
    """)
    code, out = cli_json(ws, "build", str(deck), capsys=capsys)
    assert code == 0, out["issues"]
    prs = Presentation(out["output"])
    assert len(prs.slides) == 15
    assert prs.slides[13].placeholders[1].text_frame.text.startswith('"Paper is still')
