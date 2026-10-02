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
