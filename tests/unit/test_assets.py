import yaml
from PIL import Image
from test_check import GOOD

from conftest import cli_json, codes, write_deck


def test_brand_inventory_lists_every_class(ws, capsys):
    code, out = cli_json(ws, "assets", "stock", capsys=capsys)
    assert code == 0
    by_class = {}
    for a in out["assets"]:
        by_class.setdefault(a["class"], []).append(a["id"])
    assert by_class["logo"] == ["brand:logo/primary"]
    assert by_class["icon"][0] == "brand:icon/check"  # the kit's own, then the starter icons it lacks
    starter = [a for a in out["assets"] if a.get("source") == "deck-builder starter icons"]
    assert starter and "brand:icon/check" not in {a["id"] for a in starter}
    assert {a["id"] for a in starter} >= {"brand:icon/arrow", "brand:icon/chart"}
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


def test_deck_inventory_refuses_an_asset_outside_the_deck_folder_without_reading_it(ws, capsys):
    secret = ws / "private" / "secret.png"
    secret.parent.mkdir(parents=True)
    Image.new("RGB", (10, 10)).save(secret)
    deck = write_deck(ws, f"## A\nlayout: image\n\n![x]({secret})\n")
    code, out = cli_json(ws, "assets", str(deck), capsys=capsys)
    assert code == 1
    assert codes(out) == ["ASSET_OUTSIDE"]
    entry = out["assets"][0]
    assert "sha256" not in entry and "pixels" not in entry


def test_brand_inventory_refuses_a_logo_outside_the_kit_without_reading_it(ws, capsys):
    secret = ws / "private" / "secret.png"
    secret.parent.mkdir(parents=True)
    Image.new("RGB", (10, 10)).save(secret)
    brand_yaml = ws / "brands" / "stock" / "brand.yaml"
    meta = yaml.safe_load(brand_yaml.read_text())
    meta["logos"]["escaped"] = "../../private/secret.png"
    brand_yaml.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    code, out = cli_json(ws, "assets", "stock", capsys=capsys)
    assert code == 1
    assert "ASSET_OUTSIDE" in codes(out)
    entry = next(a for a in out["assets"] if a["id"] == "brand:logo/escaped")
    assert "sha256" not in entry and "pixels" not in entry
