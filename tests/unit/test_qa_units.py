"""QA pieces that don't need a renderer: empty placeholders, font matching, PowerPoint failure paths."""
import subprocess
from pathlib import Path

import pytest

from conftest import cli_json, write_deck
from deck_builder.errors import EnvError
from deck_builder.qa import backends, fonts
from deck_builder.qa.render import empty_placeholders


def test_empty_text_field_is_flagged(ws, capsys):
    deck = write_deck(ws, "## Hello\nlayout: title\nsubtitle: ''\n")
    code, out = cli_json(ws, "build", str(deck), capsys=capsys)
    assert code == 0
    issues = empty_placeholders(Path(out["output"]))
    assert [(i.code, i.slide) for i in issues] == [("EMPTY_PLACEHOLDER", 1)]


def test_font_check_reports_fallback_and_substitution(monkeypatch):
    meta = {"fonts": {"heading": {"family": "Inter", "fallback": "Liberation Sans"},
                      "body": {"family": "Source Serif", "fallback": "Georgia"}}}
    monkeypatch.setattr(fonts, "embedded", lambda pdf: {"liberationsansbold", "dejavusans"})
    issues = fonts.check(Path("x.pdf"), meta)
    assert [i.code for i in issues] == ["MISSING_FONT", "MISSING_FONT"]
    assert "fallback" in issues[0].message and "isn't installed" in issues[1].message
    assert all(i.severity == "warning" for i in issues)


def test_font_check_passes_when_the_family_is_used(monkeypatch):
    monkeypatch.setattr(fonts, "embedded", lambda pdf: {"interbold", "intermedium"})
    assert fonts.check(Path("x.pdf"), {"fonts": {"heading": {"family": "Inter"}}}) == []


class FakeProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


@pytest.fixture
def container(tmp_path, monkeypatch):
    monkeypatch.setattr(backends, "PP_CONTAINER", tmp_path / "container")
    monkeypatch.setattr(backends, "_running", lambda: True)
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"pptx")
    return pptx


def test_powerpoint_failure_reports_office_repair(container, monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc(returncode=1, stderr="error -1708"))
    with pytest.raises(EnvError) as e:
        backends.powerpoint(container, tmp_path / "out.pdf")
    assert e.value.code == "OFFICE_REPAIR"
    assert not (backends.PP_CONTAINER / ".lock").exists()


def test_powerpoint_permission_denied_says_where_to_grant_it(container, monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeProc(returncode=1, stderr="Not authorized (-1743)"))
    with pytest.raises(EnvError) as e:
        backends.powerpoint(container, tmp_path / "out.pdf")
    assert "Privacy & Security > Automation" in str(e.value)


def test_powerpoint_timeout_leaves_it_running_and_reports(container, monkeypatch, tmp_path):
    def slow(*a, **k):
        raise subprocess.TimeoutExpired(cmd="osascript", timeout=1)

    monkeypatch.setattr(subprocess, "run", slow)
    with pytest.raises(EnvError) as e:
        backends.powerpoint(container, tmp_path / "out.pdf")
    assert e.value.code == "OFFICE_REPAIR" and "left running" in str(e.value)

