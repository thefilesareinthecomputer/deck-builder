import json
import subprocess
import sys

import pytest

from deck_builder import __version__
from deck_builder.cli import main
from deck_builder.errors import CODES, EXIT_ENV, EXIT_OK


def run(capsys, *argv):
    code = main(list(argv))
    out = capsys.readouterr()
    return code, out.out, out.err


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_command_prints_help_and_exits_2(capsys):
    code, out, _ = run(capsys)
    assert code == EXIT_ENV
    assert "<command>" in out


def test_unbuilt_command_reports_not_implemented_as_json(capsys):
    code, out, _ = run(capsys, "skills", "install", "--json")
    assert code == EXIT_ENV
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["issues"][0]["code"] == "NOT_IMPLEMENTED"


def test_docs_lists_topics(capsys):
    code, out, _ = run(capsys, "docs", "--json")
    assert code == EXIT_OK
    topics = json.loads(out)["topics"]
    assert {"codes", "deck-md", "workflow"} <= set(topics)


def test_docs_codes_covers_every_code(capsys):
    code, out, _ = run(capsys, "docs", "codes")
    assert code == EXIT_OK
    for c in CODES:
        assert f"`{c}`" in out


def test_docs_unknown_topic_exits_2(capsys):
    code, _, err = run(capsys, "docs", "nope")
    assert code == EXIT_ENV
    assert "unknown docs topic" in err


def test_explain_is_case_insensitive(capsys):
    code, out, _ = run(capsys, "explain", "budget_chars", "--json")
    assert code == EXIT_OK
    assert json.loads(out)["code"] == "BUDGET_CHARS"


def test_explain_unknown_code_exits_2(capsys):
    code, _, _ = run(capsys, "explain", "NOPE")
    assert code == EXIT_ENV


def test_installed_entry_point_runs():
    r = subprocess.run([sys.executable, "-m", "deck_builder", "--version"], capture_output=True, text=True)
    assert r.returncode == 0
    assert __version__ in r.stdout
