import json
import sys

from deck_builder import doctor
from deck_builder.cli import main
from deck_builder.doctor import Check


def test_doctor_reports_build_readiness_and_backend(ws, capsys):
    code = main(["--config", str(ws / "deck-builder.toml"), "doctor", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    names = {c["name"] for c in out["checks"]}
    assert {"python", "python-pptx", "poppler", "libreoffice", "config"} <= names
    assert out["can_build"] is True
    assert out["render_backend"] in (None, "libreoffice", "powerpoint")


def agent_check(ws, capsys):
    main(["--config", str(ws / "deck-builder.toml"), "doctor", "--json"])
    return next(c for c in json.loads(capsys.readouterr().out)["checks"] if c["name"] == "agent tools (mcp)")


def test_doctor_reports_the_agents_mcp_server_answering(ws, capsys, monkeypatch):
    monkeypatch.setattr("deck_builder.doctor.mcp_command", lambda: [sys.executable, "-m", "deck_builder"])
    check = agent_check(ws, capsys)
    assert check["status"] == "ok" and "answers with 16 tools" in check["detail"]


def test_doctor_says_how_to_install_the_cli_when_its_missing(ws, capsys, monkeypatch):
    monkeypatch.setattr("deck_builder.doctor.mcp_command", lambda: None)
    check = agent_check(ws, capsys)
    assert check["status"] == "missing" and check["fix"].startswith("uv tool install --editable ")


def test_render_backend_prefers_libreoffice_over_unverified_powerpoint():
    checks = [Check("poppler", "ok", ""), Check("libreoffice", "ok", ""), Check("powerpoint", "unverified", "")]
    assert doctor.render_backend(checks) == "libreoffice"


def test_render_backend_falls_back_to_powerpoint_without_libreoffice():
    checks = [Check("poppler", "ok", ""), Check("libreoffice", "missing", ""), Check("powerpoint", "unverified", "")]
    assert doctor.render_backend(checks) == "powerpoint"


def test_doctor_without_config_points_at_init(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DECK_BUILDER_CONFIG", raising=False)
    monkeypatch.setattr("deck_builder.config.USER_CONFIG", tmp_path / "none.toml")
    main(["doctor", "--json"])
    out = json.loads(capsys.readouterr().out)
    cfg = next(c for c in out["checks"] if c["name"] == "config")
    assert cfg["status"] == "missing" and cfg["fix"] == "deck-builder init"
