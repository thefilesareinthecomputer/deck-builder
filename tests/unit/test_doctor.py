import json

from deck_builder.cli import main


def test_doctor_reports_build_readiness_and_backend(ws, capsys):
    code = main(["--config", str(ws / "deck-builder.toml"), "doctor", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    names = {c["name"] for c in out["checks"]}
    assert {"python", "python-pptx", "poppler", "libreoffice", "config"} <= names
    assert out["can_build"] is True
    assert out["render_backend"] in (None, "libreoffice", "powerpoint")


def test_doctor_without_config_points_at_init(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DECK_BUILDER_CONFIG", raising=False)
    monkeypatch.setattr("deck_builder.config.USER_CONFIG", tmp_path / "none.toml")
    main(["doctor", "--json"])
    out = json.loads(capsys.readouterr().out)
    cfg = next(c for c in out["checks"] if c["name"] == "config")
    assert cfg["status"] == "missing" and cfg["fix"] == "deck-builder init"
