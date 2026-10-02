from test_check import GOOD

from conftest import cli_json, codes, write_deck


def test_brand_inventory_lists_every_class(ws, capsys):
    code, out = cli_json(ws, "assets", "stock", capsys=capsys)
    assert code == 0
    by_class = {}
    for a in out["assets"]:
        by_class.setdefault(a["class"], []).append(a["id"])
    assert by_class["logo"] == ["brand:logo/primary"]
    assert by_class["icon"] == ["brand:icon/check"]
    assert "primary" in by_class["color"]
    logo = next(a for a in out["assets"] if a["class"] == "logo")
    assert logo["pixels"] == [400, 200] and len(logo["sha256"]) == 64


def test_deck_inventory_maps_assets_to_slides(ws, capsys):
    deck = write_deck(ws, GOOD)
    code, out = cli_json(ws, "assets", str(deck), capsys=capsys)
    assert code == 0
    assert {a["id"]: a["slides"] for a in out["assets"]} == {"brand:icon/check": [7], "brand:logo/primary": [6]}


def test_deck_inventory_flags_unknown_assets(ws, capsys):
    deck = write_deck(ws, "## A\nlayout: image\n\n![x](brand:logo/nope)\n")
    code, out = cli_json(ws, "assets", str(deck), capsys=capsys)
    assert code == 1
    assert codes(out) == ["UNKNOWN_ASSET"]
