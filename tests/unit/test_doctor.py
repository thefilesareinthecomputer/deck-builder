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


class FakeDist:
    def __init__(self, raw: str | None) -> None:
        self._raw = raw

    def read_text(self, name: str) -> str | None:
        return self._raw


def test_editable_install_true_when_direct_url_says_so(monkeypatch):
    monkeypatch.setattr(doctor.md, "distribution",
                        lambda name: FakeDist('{"url": "file:///x", "dir_info": {"editable": true}}'))
    assert doctor.editable_install() is True


def test_editable_install_false_for_a_regular_install(monkeypatch):
    monkeypatch.setattr(doctor.md, "distribution", lambda name: FakeDist(None))
    assert doctor.editable_install() is False


def test_editable_install_false_when_the_package_isnt_found(monkeypatch):
    def boom(name):
        raise doctor.md.PackageNotFoundError(name)

    monkeypatch.setattr(doctor.md, "distribution", boom)
    assert doctor.editable_install() is False


def test_doctor_warns_in_human_output_and_json_when_editable(ws, capsys, monkeypatch):
    monkeypatch.setattr("deck_builder.doctor.editable_install", lambda: True)
    code = main(["--config", str(ws / "deck-builder.toml"), "doctor", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["editable_install"] is True

    main(["--config", str(ws / "deck-builder.toml"), "doctor"])
    text = capsys.readouterr().out
    assert "warning" in text and "editable install" in text and "outside the clone" in text


def test_doctor_has_no_editable_warning_when_not_editable(ws, capsys, monkeypatch):
    monkeypatch.setattr("deck_builder.doctor.editable_install", lambda: False)
    main(["--config", str(ws / "deck-builder.toml"), "doctor", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["editable_install"] is False

    main(["--config", str(ws / "deck-builder.toml"), "doctor"])
    assert "editable install" not in capsys.readouterr().out
