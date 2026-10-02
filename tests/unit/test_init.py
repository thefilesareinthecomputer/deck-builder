import hashlib
import json

from deck_builder.cli import main


def run(*argv, capsys):
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def tree_hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def test_init_creates_everything_once(tmp_path, capsys):
    code, out = run("init", "--dir", str(tmp_path), capsys=capsys)
    assert code == 0
    assert (tmp_path / "deck-builder.toml").is_file()
    assert (tmp_path / "workspace" / "brands" / "neutral" / "template.potx").is_file()
    assert (tmp_path / "workspace" / "decks" / "quarterly-review" / "deck.md").is_file()
    before = tree_hashes(tmp_path)
    code, out = run("init", "--dir", str(tmp_path), capsys=capsys)
    assert code == 0 and out["created"] == []
    assert tree_hashes(tmp_path) == before


def test_neutral_brand_is_valid(tmp_path, capsys):
    run("init", "--dir", str(tmp_path), capsys=capsys)
    cfg = str(tmp_path / "deck-builder.toml")
    code, out = run("--config", cfg, "brand", "check", "neutral", capsys=capsys)
    assert code == 0, out["issues"]


def test_example_decks_build_clean(tmp_path, capsys):
    run("init", "--dir", str(tmp_path), capsys=capsys)
    cfg = str(tmp_path / "deck-builder.toml")
    decks = tmp_path / "workspace" / "decks"
    code, out = run("--config", cfg, "build", str(decks / "quarterly-review" / "deck.md"), capsys=capsys)
    assert code == 0, out["issues"]
    assert out["issues"] == [], out["issues"]
    assert out["output"].endswith("workspace/out/quarterly-review.pptx")
    code, out = run("--config", cfg, "build", str(decks / "bulk-outreach" / "deck.md"),
                    "--data", str(decks / "bulk-outreach" / "clients.csv"), "--name", "{{client}}-review.pptx",
                    capsys=capsys)
    assert code == 0, out["issues"]
    assert len(out["outputs"]) == 3
