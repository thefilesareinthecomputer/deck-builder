"""What this machine can do: build (Python only), render (PowerPoint or LibreOffice, plus poppler)."""
from __future__ import annotations

import importlib.metadata as md
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
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


def install_hint() -> str:
    clone = Path(__file__).resolve().parents[2]
    return f"uv tool install --editable {clone if (clone / 'pyproject.toml').is_file() else '<clone>'}"


def editable_install() -> bool:
    """Whether the running deck_builder package is `pip install -e` / `uv sync`'s editable install, straight
    from this clone's src/: the agents' MCP server then runs this clone's code live, not an installed copy."""
    try:
        dist = md.distribution("deck-builder")
    except md.PackageNotFoundError:
        return False
    raw = dist.read_text("direct_url.json")
    if not raw:
        return False
    try:
        data = json.loads(raw)
    except ValueError:
        return False
    return bool(data.get("dir_info", {}).get("editable"))


def mcp_command() -> list[str] | None:
    """How Claude Code starts the agents' MCP server: `deck-builder mcp`, found on PATH."""
    exe = shutil.which("deck-builder")
    return [exe] if exe else None


def agent_tools(cfg: cfgmod.Config) -> Check:
    """The deck agents have no shell: they reach the engine only through `deck-builder mcp`."""
    name = "agent tools (mcp)"
    cmd = mcp_command()
    if cmd is None:
        return Check(name, "missing", "deck-builder isn't on PATH, so the agents' MCP server can't start",
                     install_hint())
    if not cfg.found:
        return Check(name, "missing", "no deck-builder.toml for the MCP server to confine its tools to",
                     "deck-builder init")
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
    try:
        proc = subprocess.run([*cmd, "--config", str(cfg.path), "mcp"], capture_output=True, text=True, timeout=60,
                              input="".join(json.dumps(m) + "\n" for m in msgs))
        tools_ = json.loads(proc.stdout.splitlines()[-1])["result"]["tools"]
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, IndexError):
        return Check(name, "missing", "`deck-builder mcp` didn't answer tools/list", install_hint())
    return Check(name, "ok", f"`deck-builder mcp` answers with {len(tools_)} tools")


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
    checks.append(agent_tools(cfg))
    return checks


def render_backend(checks: list[Check]) -> str | None:
    status = {c.name: c.status for c in checks}
    if status.get("poppler") != "ok":
        return None
    if status.get("powerpoint") == "unverified":
        return "powerpoint"
    return "libreoffice" if status.get("libreoffice") == "ok" else None
