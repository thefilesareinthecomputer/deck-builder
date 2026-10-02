import json
from pathlib import Path

import pytest

from deck_builder.cli import main

REPO = Path(__file__).resolve().parents[2]


def run(*argv, capsys):
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture(autouse=True)
def cli_on_path(monkeypatch):
    monkeypatch.setattr("deck_builder.doctor.mcp_command", lambda: ["deck-builder"])


def test_install_refuses_without_the_cli_on_path(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(REPO)
    monkeypatch.setattr("deck_builder.doctor.mcp_command", lambda: None)
    code, out = run("skills", "install", "--target", str(tmp_path), "--yes", capsys=capsys)
    assert code == 2 and f"uv tool install --editable {REPO}" in out["error"]
    assert list(tmp_path.iterdir()) == []


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


def test_outside_a_clone_it_links_the_clone_the_engine_runs_from(tmp_path, capsys, monkeypatch):
    """`uv run --project <clone>` or an editable install, run from another repo."""
    monkeypatch.chdir(tmp_path)
    code, out = run("skills", "install", "--target", str(tmp_path / "home"), capsys=capsys)
    assert code == 0 and str(REPO) in json.dumps(out["links"])


def test_no_clone_anywhere_is_an_environment_error(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("deck_builder.skills.__file__", str(tmp_path / "site" / "deck_builder" / "skills.py"))
    code, out = run("skills", "install", capsys=capsys)
    assert code == 2 and "clone" in out["error"]
