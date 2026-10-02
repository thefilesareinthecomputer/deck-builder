"""Where the CLI reads decks from and writes to, and the hints it prints when a path is wrong."""
import json
from pathlib import Path

from test_check import GOOD

from conftest import cli_json, write_deck
from deck_builder.cli import main


def test_check_and_build_accept_the_deck_folder(ws, capsys):
    write_deck(ws, GOOD)
    code, out = cli_json(ws, "check", str(ws / "decks"), capsys=capsys)
    assert code == 0, out["issues"]
    assert out["input"] == str(ws / "decks" / "deck.md")
    code, out = cli_json(ws, "build", str(ws / "decks"), capsys=capsys)
    assert code == 0, out["issues"]
    assert Path(out["output"]) == ws / "out" / "decks.pptx"


def test_a_folder_without_a_deck_file_is_a_clear_error(ws, capsys):
    code, out = cli_json(ws, "check", str(ws / "decks"), capsys=capsys)
    assert code == 2
    assert "no deck.md, deck.xlsx, deck.csv in" in out["error"]


def test_a_folder_with_two_deck_files_is_ambiguous(ws, capsys):
    write_deck(ws, GOOD)
    (ws / "decks" / "deck.csv").write_text("title\nAnother deck\n")
    code, out = cli_json(ws, "check", str(ws / "decks"), capsys=capsys)
    assert code == 2
    assert out["code"] == "AMBIGUOUS_DECK"
    assert "deck.md" in out["error"] and "deck.csv" in out["error"]


def test_build_output_to_an_existing_folder(ws, capsys):
    deck = write_deck(ws, GOOD)
    (ws / "outbox").mkdir()
    code, out = cli_json(ws, "build", str(deck), "-o", str(ws / "outbox"), capsys=capsys)
    assert code == 0, out["issues"]
    assert Path(out["output"]) == ws / "outbox" / "decks.pptx"
    assert Path(out["output"]).is_file()


def test_build_output_to_a_new_folder_with_a_trailing_slash(ws, capsys):
    deck = write_deck(ws, GOOD)
    code, out = cli_json(ws, "build", str(deck), "-o", f"{ws / 'new'}/", capsys=capsys)
    assert code == 0, out["issues"]
    assert Path(out["output"]) == ws / "new" / "decks.pptx"
    assert Path(out["output"]).is_file()


def test_render_given_a_deck_points_at_check_render(ws, capsys):
    deck = write_deck(ws, GOOD)
    for target in (deck, deck.parent):
        code, out = cli_json(ws, "render", str(target), capsys=capsys)
        assert code == 2
        assert f"check {target} --render" in out["error"]


def test_render_rejects_a_file_that_isnt_a_pptx(ws, capsys):
    other = ws / "notes.txt"
    other.write_text("not a deck")
    code, out = cli_json(ws, "render", str(other), capsys=capsys)
    assert code == 2
    assert "render takes a .pptx file, not .txt" in out["error"]


def test_unknown_brand_without_a_config_says_to_run_init(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DECK_BUILDER_CONFIG", raising=False)
    monkeypatch.setattr("deck_builder.config.USER_CONFIG", tmp_path / "none.toml")
    assert main(["brand", "check", "acme", "--json"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["code"] == "UNKNOWN_BRAND"
    assert "no deck-builder.toml in this folder or above it" in out["error"]
    assert "`deck-builder init`" in out["error"]


def test_unknown_brand_with_a_config_has_no_init_hint(ws, capsys):
    code, out = cli_json(ws, "brand", "check", "acme", capsys=capsys)
    assert code == 2
    assert out["code"] == "UNKNOWN_BRAND"
    assert "deck-builder init" not in out["error"]


def test_human_output_names_explain_for_the_error_codes(ws, capsys):
    deck = write_deck(ws, "## A\nlayout: nope\n\n## B — synergy\nlayout: title\n")
    code, payload = cli_json(ws, "check", str(deck), capsys=capsys)
    errors = sorted({i["code"] for i in payload["issues"] if i["severity"] == "error"})
    assert len(errors) >= 2
    main(["--config", str(ws / "deck-builder.toml"), "check", str(deck)])
    hints = [ln for ln in capsys.readouterr().err.splitlines() if ln.startswith("for the fix:")]
    assert hints == [f"for the fix: deck-builder explain {errors[0]} (also {', '.join(errors[1:])})"]


def test_human_output_without_errors_has_no_explain_line(ws, capsys):
    main(["--config", str(ws / "deck-builder.toml"), "check", str(write_deck(ws, GOOD))])
    assert "for the fix:" not in capsys.readouterr().err


def test_init_creates_a_folder_that_doesnt_exist(tmp_path, capsys):
    root = tmp_path / "talks" / "q4"
    assert main(["init", "--dir", str(root), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert (root / "deck-builder.toml").is_file()
    assert str(root) in out["created"]


def test_init_on_a_file_is_a_clear_error(tmp_path, capsys):
    target = tmp_path / "deck.md"
    target.write_text("## A\n")
    assert main(["init", "--dir", str(target), "--json"]) == 2
    assert "init needs a folder" in json.loads(capsys.readouterr().out)["error"]
