"""Headless LibreOffice on macOS gets a fontconfig that sees the system's fonts."""
import contextlib
import xml.etree.ElementTree as ET
from pathlib import Path

from deck_builder.qa import backends


def test_lo_env_on_macos_points_fontconfig_at_the_system_fonts(tmp_path, monkeypatch):
    monkeypatch.setattr(backends.sys, "platform", "darwin")
    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    monkeypatch.setattr(backends, "FONT_CACHE", tmp_path / "a & b" / "cache")
    env = backends.lo_env(str(tmp_path))
    conf = Path(env["FONTCONFIG_FILE"])
    assert conf == tmp_path / "fonts.conf"
    root = ET.parse(conf).getroot()  # well-formed even with & in a path
    assert [d.text for d in root.iter("dir")] == list(backends.MAC_FONT_DIRS)
    assert root.find("cachedir").text == str(tmp_path / "a & b" / "cache")


def test_lo_env_keeps_a_fontconfig_the_caller_set(tmp_path, monkeypatch):
    monkeypatch.setattr(backends.sys, "platform", "darwin")
    monkeypatch.setenv("FONTCONFIG_FILE", "/etc/fonts/custom.conf")
    assert backends.lo_env(str(tmp_path))["FONTCONFIG_FILE"] == "/etc/fonts/custom.conf"
    assert not (tmp_path / "fonts.conf").exists()


def test_lo_env_elsewhere_is_the_plain_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(backends.sys, "platform", "linux")
    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    assert "FONTCONFIG_FILE" not in backends.lo_env(str(tmp_path))
    assert not (tmp_path / "fonts.conf").exists()


def test_libreoffice_runs_with_that_environment(tmp_path, monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen.update(kw)
        raise backends.subprocess.TimeoutExpired(cmd, 1)

    monkeypatch.setattr(backends.sys, "platform", "darwin")
    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    monkeypatch.setattr(backends.tools, "soffice", lambda: "/usr/bin/soffice")
    monkeypatch.setattr(backends.subprocess, "run", fake_run)
    pptx = tmp_path / "d.pptx"
    pptx.write_bytes(b"")
    with contextlib.suppress(backends.EnvError):
        backends.libreoffice(pptx, tmp_path / "d.pdf")
    assert seen["env"]["FONTCONFIG_FILE"].endswith("fonts.conf")
