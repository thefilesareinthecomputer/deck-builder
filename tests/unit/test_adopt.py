import yaml
from pptx import Presentation

from conftest import cli_json, write_deck


def stock_template(path):
    Presentation().save(str(path))
    return path


def test_inspect_lists_layouts_and_theme(ws, capsys, tmp_path):
    t = stock_template(tmp_path / "client.pptx")
    code, out = cli_json(ws, "inspect", str(t), capsys=capsys)
    assert code == 0
    names = [lay["name"] for lay in out["layouts"]]
    assert "Title and Content" in names
    assert out["theme"]["colors"]["accent1"]
    assert out["theme"]["fonts"]["heading"]


def test_inspect_yaml_is_a_valid_tokens_starter(ws, capsys, tmp_path):
    from deck_builder.brand import schema

    t = stock_template(tmp_path / "client.pptx")
    code, out = cli_json(ws, "inspect", str(t), "--yaml", capsys=capsys)
    assert code == 0
    assert schema.errors("tokens", out["tokens"]) == []
    content = out["tokens"]["layouts"]["title-and-content"]["fields"]
    assert content["title"]["kind"] == "text" and content["body"]["kind"] == "bullets"


def test_adopt_wraps_a_template_into_a_valid_kit(ws, capsys, tmp_path):
    t = stock_template(tmp_path / "client.pptx")
    code, out = cli_json(ws, "brand", "adopt", "halvorsen", "--template", str(t), capsys=capsys)
    assert code == 0, out["issues"]
    kit = ws / "brands" / "halvorsen"
    assert (kit / "template.pptx").is_file()
    meta = yaml.safe_load((kit / "brand.yaml").read_text())
    assert meta["slug"] == "halvorsen"
    assert meta["theme_colors"]["accent1"] == "accent1"
    code, out = cli_json(ws, "brand", "check", "halvorsen", capsys=capsys)
    assert code == 0, out["issues"]


def test_adopted_kit_builds_a_deck(ws, capsys, tmp_path):
    t = stock_template(tmp_path / "client.pptx")
    cli_json(ws, "brand", "adopt", "halvorsen", "--template", str(t), capsys=capsys)
    deck = write_deck(ws, "---\nbrand: halvorsen\n---\n\n## Hello\nlayout: title-and-content\n\n- one\n- two\n")
    code, out = cli_json(ws, "build", str(deck), capsys=capsys)
    assert code == 0, out["issues"]


def test_adopt_refuses_to_overwrite(ws, capsys, tmp_path):
    t = stock_template(tmp_path / "client.pptx")
    cli_json(ws, "brand", "adopt", "halvorsen", "--template", str(t), capsys=capsys)
    code, out = cli_json(ws, "brand", "adopt", "halvorsen", "--template", str(t), capsys=capsys)
    assert code == 2 and "--force" in out["error"]


def test_adopt_rejects_a_bad_slug(ws, capsys, tmp_path):
    t = stock_template(tmp_path / "client.pptx")
    code, out = cli_json(ws, "brand", "adopt", "Bad Slug", "--template", str(t), capsys=capsys)
    assert code == 2


def test_adopt_with_force_removes_a_stale_potx(ws, capsys, tmp_path):
    t = stock_template(tmp_path / "client.pptx")
    cli_json(ws, "brand", "adopt", "halvorsen", "--template", str(t), capsys=capsys)
    kit = ws / "brands" / "halvorsen"
    stale = kit / "template.potx"
    stale.write_bytes(b"stale potx, as if `brand init` had made this kit before")
    code, out = cli_json(ws, "brand", "adopt", "halvorsen", "--template", str(t), "--force", capsys=capsys)
    assert code == 0, out["issues"]
    assert (kit / "template.pptx").is_file()
    assert not stale.exists()


def test_brand_check_refuses_a_kit_with_both_template_files(ws, capsys, tmp_path):
    t = stock_template(tmp_path / "client.pptx")
    cli_json(ws, "brand", "adopt", "halvorsen", "--template", str(t), capsys=capsys)
    kit = ws / "brands" / "halvorsen"
    (kit / "template.potx").write_bytes(b"stale potx left behind by hand")
    code, out = cli_json(ws, "brand", "check", "halvorsen", capsys=capsys)
    assert code == 1
    msg = " ".join(i["message"] for i in out["issues"])
    assert "template.potx" in msg and "template.pptx" in msg


def test_build_refuses_a_kit_with_both_template_files(ws, capsys, tmp_path):
    t = stock_template(tmp_path / "client.pptx")
    cli_json(ws, "brand", "adopt", "halvorsen", "--template", str(t), capsys=capsys)
    kit = ws / "brands" / "halvorsen"
    (kit / "template.potx").write_bytes(b"stale potx left behind by hand")
    deck = write_deck(ws, "---\nbrand: halvorsen\n---\n\n## Hello\nlayout: title-and-content\n\n- one\n- two\n")
    code, out = cli_json(ws, "build", str(deck), capsys=capsys)
    assert code == 1
    msg = " ".join(i["message"] for i in out["issues"])
    assert "template.potx" in msg and "template.pptx" in msg
