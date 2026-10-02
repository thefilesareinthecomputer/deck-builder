"""What this machine can do: build (Python only), render (PowerPoint or LibreOffice, plus poppler)."""
from __future__ import annotations

import importlib.metadata as md
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from deck_builder import config as cfgmod
from deck_builder.qa import tools

PACKAGES = ("python-pptx", "pyyaml", "openpyxl", "defusedxml", "jsonschema", "pillow")


@dataclass
class Check:
    name: str
    status: str  # ok | missing | optional | unverified
    detail: str
    fix: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v}


def automation_permission() -> Check:
    """Asks PowerPoint for its presentation count, which launches it if needed and triggers the macOS prompt."""
    proc = subprocess.run(["osascript", "-e", 'tell application "Microsoft PowerPoint" to count presentations'],
                          capture_output=True, text=True, timeout=60)
    if "-1743" in proc.stderr:
        return Check("powerpoint automation", "missing", "macOS denied control of PowerPoint",
                     "System Settings > Privacy & Security > Automation: allow the app running deck-builder to "
                     "control Microsoft PowerPoint")
    if proc.returncode != 0:
        return Check("powerpoint automation", "missing", proc.stderr.strip() or "osascript failed")
    return Check("powerpoint automation", "ok", "PowerPoint answered")


def run(cfg: cfgmod.Config, test_powerpoint: bool) -> list[Check]:
    checks = [Check("python", "ok" if sys.version_info >= (3, 11) else "missing", sys.version.split()[0],
                    "" if sys.version_info >= (3, 11) else "install Python 3.11 or later")]
    for pkg in PACKAGES:
        try:
            checks.append(Check(pkg, "ok", md.version(pkg)))
        except md.PackageNotFoundError:
            checks.append(Check(pkg, "missing", "not installed", "uv sync"))
    missing = tools.poppler_missing()
    checks.append(Check("poppler", "missing" if missing else "ok",
                        f"{', '.join(missing)} not found" if missing else "pdftoppm, pdftotext, pdffonts",
                        tools.install_hint("poppler") if missing else ""))
    lo = tools.soffice()
    pp = tools.powerpoint()
    checks.append(Check("libreoffice", "ok" if lo else ("optional" if pp else "missing"), lo or "not found",
                        "" if lo or pp else tools.install_hint("libreoffice")))
    if sys.platform == "darwin":
        checks.append(Check("powerpoint", "unverified" if pp else "optional",
                            "installed; backend not yet verified (scripts/probe_powerpoint.sh)" if pp
                            else "not installed; renders use LibreOffice"))
        if pp and test_powerpoint:
            checks.append(automation_permission())
    checks.append(Check("config", "ok" if cfg.found else "missing",
                        str(cfg.path) if cfg.found else "no deck-builder.toml",
                        "" if cfg.found else "deck-builder init"))
    return checks


def render_backend(checks: list[Check]) -> str | None:
    status = {c.name: c.status for c in checks}
    if status.get("poppler") != "ok":
        return None
    if status.get("powerpoint") == "unverified":
        return "powerpoint"
    return "libreoffice" if status.get("libreoffice") == "ok" else None
