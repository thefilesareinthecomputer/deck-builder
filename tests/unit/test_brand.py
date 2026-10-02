import json

import yaml
from test_check import GOOD

from conftest import cli_json, codes, write_deck
from deck_builder.brand import schema


def test_brand_list(ws, capsys):
    code, out = cli_json(ws, "brand", "list", capsys=capsys)
    assert code == 0
    assert [b["slug"] for b in out["brands"]] == ["stock"]
    assert out["brands"][0]["valid"] is True


def test_brand_list_without_config_says_how_to_start(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DECK_BUILDER_CONFIG", raising=False)
    monkeypatch.setattr("deck_builder.config.USER_CONFIG", tmp_path / "none.toml")
    from deck_builder.cli import main

    assert main(["brand", "list", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["config"] is None and out["brands"] == []


def test_brand_show_is_compact(ws, capsys):
    code, out = cli_json(ws, "brand", "show", "stock", capsys=capsys)
    assert code == 0
    assert out["layouts"]["content"]["fields"]["body"] == "bullets<=300 x5<=80"
    assert out["layouts"]["big-number"]["heading"] == "number"
    assert out["logos"] == ["primary"] and out["icons"] == ["check"]
    assert len(json.dumps(out)) < 4096


def test_brand_check_passes_on_a_good_kit(ws, capsys):
    code, out = cli_json(ws, "brand", "check", "stock", capsys=capsys)
    assert code == 0, out["issues"]


def test_brand_check_finds_mapping_and_reference_errors(ws, capsys):
    kit = ws / "brands" / "stock"
    tokens = yaml.safe_load((kit / "tokens.yaml").read_text())
    tokens["layouts"]["content"]["fields"]["body"]["idx"] = 9
    tokens["layouts"]["two-col"]["template_layout"] = "Nope"
    tokens["chart"]["colors"] = ["primary", "chartreuse"]
    (kit / "tokens.yaml").write_text(yaml.safe_dump(tokens))
    (kit / "assets" / "logo.png").unlink()
    code, out = cli_json(ws, "brand", "check", "stock", capsys=capsys)
    assert code == 1
    assert sorted(set(codes(out))) == ["MISSING_IMAGE", "TEMPLATE_MISMATCH", "UNKNOWN_ASSET"]


def test_brand_check_finds_duplicate_idx_within_a_layout(ws, capsys):
    kit = ws / "brands" / "stock"
    tokens = yaml.safe_load((kit / "tokens.yaml").read_text())
    fields = tokens["layouts"]["content"]["fields"]
    fields["body"]["idx"] = fields["title"]["idx"]  # title and body now fill/clear the same placeholder
    (kit / "tokens.yaml").write_text(yaml.safe_dump(tokens))
    code, out = cli_json(ws, "brand", "check", "stock", capsys=capsys)
    assert code == 1
    msg = " ".join(i["message"] for i in out["issues"])
    assert "content" in msg and "title" in msg and "body" in msg


def test_build_refuses_a_kit_with_duplicate_idx(ws, capsys):
    kit = ws / "brands" / "stock"
    tokens = yaml.safe_load((kit / "tokens.yaml").read_text())
    fields = tokens["layouts"]["content"]["fields"]
    fields["body"]["idx"] = fields["title"]["idx"]
    (kit / "tokens.yaml").write_text(yaml.safe_dump(tokens))
    code, out = cli_json(ws, "build", str(write_deck(ws, GOOD)), capsys=capsys)
    assert code == 1
    msg = " ".join(i["message"] for i in out["issues"])
    assert "content" in msg and "title" in msg and "body" in msg


def test_schema_errors_are_all_reported(ws, capsys):
    kit = ws / "brands" / "stock"
    meta = yaml.safe_load((kit / "brand.yaml").read_text())
    meta["palette"]["primary"] = "blue"
    meta["version"] = "one"
    meta["colour"] = "typo"
    (kit / "brand.yaml").write_text(yaml.safe_dump(meta))
    code, out = cli_json(ws, "brand", "check", "stock", capsys=capsys)
    assert code == 1
    assert codes(out).count("SCHEMA") == 3


def test_schema_command_prints_each_schema(ws, capsys):
    for name in schema.NAMES:
        code, out = cli_json(ws, "schema", name, capsys=capsys)
        assert code == 0
        assert out["schema"]["$schema"].startswith("https://json-schema.org/")
