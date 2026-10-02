import json
from pathlib import Path

from deck_builder.cli import main

REPO = Path(__file__).resolve().parents[2]


def run(*argv, capsys):
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def test_plan_changes_nothing_without_yes(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(REPO)
    code, out = run("skills", "install", "--target", str(tmp_path), capsys=capsys)
    assert code == 0 and out["applied"] is False
    assert {x["status"] for x in out["links"]} == {"create"}
    assert list(tmp_path.iterdir()) == []


def test_yes_links_skills_and_agent_and_is_idempotent(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(REPO)
    run("skills", "install", "--target", str(tmp_path), "--yes", capsys=capsys)
    link = tmp_path / "skills" / "deck-builder"
    assert link.is_symlink() and (link / "SKILL.md").is_file()
    assert (tmp_path / "agents" / "deck-builder-agent.md").is_symlink()
    code, out = run("skills", "install", "--target", str(tmp_path), "--yes", capsys=capsys)
    assert {x["status"] for x in out["links"]} == {"linked"}


def test_existing_files_are_left_alone(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(REPO)
    mine = tmp_path / "skills" / "deck-brand"
    mine.mkdir(parents=True)
    (mine / "SKILL.md").write_text("my own")
    code, out = run("skills", "install", "--target", str(tmp_path), "--yes", capsys=capsys)
    assert code == 0
    assert [i["code"] for i in out["issues"]] == ["SKILL_CONFLICT"]
    assert (mine / "SKILL.md").read_text() == "my own"


def test_outside_a_clone_is_an_environment_error(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out = run("skills", "install", capsys=capsys)
    assert code == 2 and "clone" in out["error"]
