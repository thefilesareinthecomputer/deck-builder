"""Security hardening from the pre-push review."""
import pytest
import yaml
from test_generate import BRAND, source

from conftest import cli_json, codes, write_deck
from deck_builder.commands import init_kit, inside
from deck_builder.errors import EnvError


@pytest.mark.parametrize("rel", ["../../CLAUDE.md", "/etc/passwd", "assets/../../x.png", "~/x.png"])
def test_brand_yaml_paths_outside_the_folder_fail_the_schema(ws, capsys, tmp_path, rel):
    src = source(tmp_path)
    meta = yaml.safe_load(src.read_text())
    meta["logos"]["primary"] = rel
    src.write_text(yaml.safe_dump(meta))
    code, out = cli_json(ws, "brand", "init", "pemberton", "--from", str(src), capsys=capsys)
    assert code == 1 and "SCHEMA" in codes(out)
    assert not (ws / "brands" / "pemberton").exists()


def test_init_kit_refuses_escaping_paths_even_without_the_schema(tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("keep me")
    src = tmp_path / "src"
    (src / "a" / "b").mkdir(parents=True)
    (src / "brand.yaml").write_text("x")
    meta = {**BRAND, "logos": {"primary": "../victim.txt"}}
    with pytest.raises(EnvError):
        init_kit(meta, src / "brand.yaml", tmp_path / "kit")
    assert victim.read_text() == "keep me"


def test_inside_allows_normal_paths(tmp_path):
    assert inside(tmp_path, "assets/logo.png") == (tmp_path / "assets" / "logo.png").resolve()


def test_render_refuses_to_delete_a_folder_it_did_not_make(ws, capsys):
    deck = write_deck(ws, "## Hello\nlayout: title\n")
    _, out = cli_json(ws, "build", str(deck), capsys=capsys)
    pptx = ws / "out" / "decks.pptx"
    mine = pptx.with_name("decks.render")
    mine.mkdir()
    (mine / "notes.txt").write_text("not a render")
    code, out = cli_json(ws, "render", str(pptx), "--backend", "libreoffice", capsys=capsys)
    assert code == 2
    assert (mine / "notes.txt").read_text() == "not a render"


def test_oversized_template_is_refused(tmp_path, monkeypatch):
    from pptx import Presentation

    from deck_builder import template

    p = tmp_path / "t.pptx"
    Presentation().save(str(p))
    monkeypatch.setattr(template, "MAX_UNPACKED", 10)
    with pytest.raises(EnvError):
        template.open_template(p)


# Bad files a user hands over: a clear error naming the file, never a traceback.

@pytest.mark.parametrize("name, text", [("deck.md", "## Caf\xe9\nlayout: title\n"),
                                        ("deck.csv", "layout,title\ntitle,Caf\xe9\n")])
def test_a_deck_file_that_isnt_utf8_is_a_clear_error(ws, capsys, name, text):
    p = ws / "decks" / name
    p.write_bytes(text.encode("cp1252"))
    code, out = cli_json(ws, "check", str(p), capsys=capsys)
    assert code == 2 and "isn't UTF-8" in out["error"] and name in out["error"]


def test_a_corrupt_workbook_given_as_bulk_data_is_a_clear_error(ws, capsys):
    deck = write_deck(ws, "## {{name}}\nlayout: title\n")
    data = ws / "decks" / "rows.xlsx"
    data.write_text("not a workbook")
    code, out = cli_json(ws, "build", str(deck), "--data", str(data), capsys=capsys)
    assert code == 2 and "rows.xlsx" in out["error"]


def test_a_file_that_isnt_an_image_fails_check_before_the_build(ws, capsys):
    (ws / "decks" / "assets").mkdir()
    (ws / "decks" / "assets" / "p.png").write_text("<html>a saved web page</html>")
    deck = write_deck(ws, "## A\nlayout: image\n\n![A photo](assets/p.png)\n")
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert code == 1 and "ASSET_FORMAT" in codes(out)


def test_brand_init_from_malformed_yaml_is_a_clear_error(ws, capsys, tmp_path):
    src = tmp_path / "brand.yaml"
    src.write_text('name: "unclosed\n')
    code, out = cli_json(ws, "brand", "init", "acme", "--from", str(src), capsys=capsys)
    assert code == 2 and "isn't valid YAML" in out["error"]


def test_a_render_setting_that_isnt_a_number_names_the_key(ws, capsys):
    (ws / "deck-builder.toml").write_text('workspace = "."\nbrand_paths = ["brands"]\n[render]\ndpi = "high"\n')
    code, out = cli_json(ws, "brand", "list", capsys=capsys)
    assert code == 2 and "render.dpi" in out["error"]


BOM = chr(0xFEFF)  # the byte-order mark some Windows editors put at the start of a UTF-8 file


@pytest.mark.parametrize("head", [BOM + "---\n", "--- \n"])
def test_front_matter_is_read_past_a_byte_order_mark_or_a_trailing_space(ws, capsys, head):
    p = ws / "decks" / "deck.md"
    p.write_text(head + "brand: nope\n---\n\n## A\nlayout: title\n", encoding="utf-8")
    code, out = cli_json(ws, "check", str(p), capsys=capsys)
    assert out.get("code") == "UNKNOWN_BRAND"  # the front matter was read, so its brand was looked up


def test_front_matter_without_a_closing_line_is_reported(ws, capsys):
    deck = write_deck(ws, "---\nbrand: stock\n\n## A\nlayout: title\n")
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert code == 1 and "PARSE" in codes(out)


def test_check_render_without_a_renderer_stops_before_building(ws, capsys, monkeypatch):
    from deck_builder.qa import backends

    def no_renderer(_requested):
        raise EnvError("no renderer: install LibreOffice")

    monkeypatch.setattr(backends, "choose", no_renderer)
    deck = write_deck(ws, "## A\nlayout: title\n")
    code, out = cli_json(ws, "check", str(deck), "--render", capsys=capsys)
    assert code == 2 and "no renderer" in out["error"]
    assert not [p for p in ws.rglob("*.pptx") if "brands" not in p.parts]  # the kit's template doesn't count


def test_an_unexpected_error_is_still_one_json_object_with_exit_2(ws, capsys, monkeypatch):
    from deck_builder import pipeline

    def boom(_path):
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline, "deck_path", boom)
    code, out = cli_json(ws, "check", str(ws / "decks"), capsys=capsys)
    assert code == 2 and "internal error" in out["error"] and "RuntimeError: boom" in out["error"]
