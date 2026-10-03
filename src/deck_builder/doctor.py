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

PACKAGES = ("python-pptx", "pyyaml", "openpyxl", "defusedxml", "jsonschema", "pillow", "pygments")


@dataclass
class Check:
    name: str
    status: str  # ok | missing | optional | unverified | stale
    detail: str
    fix: str = ""
    editable: bool | None = None  # agent_tools only: whether the probed `deck-builder mcp` process is editable
    version: str | None = None  # agent_tools only: the version the probed `deck-builder mcp` process reports

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
    """The deck agents have no shell: they reach the engine only through `deck-builder mcp`.

    `deck-builder` on PATH can be a different install than the one running this `doctor` command
    (this process might be `uv run` inside the clone's venv while PATH resolves a `uv tool install`
    elsewhere, or the reverse): spawn it and ask its own `initialize` reply whether *that* process is
    editable, rather than trusting editable_install()'s read of this process's own distribution.
    """
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
        replies = [json.loads(ln) for ln in proc.stdout.splitlines()]
        tools_ = replies[1]["result"]["tools"]
        editable = bool(replies[0]["result"]["serverInfo"].get("editable"))
        version = str(replies[0]["result"]["serverInfo"].get("version") or "") or None
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, IndexError):
        return Check(name, "missing", "`deck-builder mcp` didn't answer tools/list", install_hint())
    return Check(name, "ok", f"`deck-builder mcp` answers with {len(tools_)} tools", editable=editable,
                 version=version)


def clone_version(start: Path) -> str | None:
    """The version in the deck-builder clone at or above start, when doctor runs inside one."""
    import tomllib

    for folder in (start, *start.parents):
        p = folder / "pyproject.toml"
        if p.is_file():
            try:
                project = tomllib.loads(p.read_text(encoding="utf-8")).get("project") or {}
            except (OSError, tomllib.TOMLDecodeError):
                return None
            return str(project["version"]) if project.get("name") == "deck-builder" and "version" in project else None
    return None


def install_version(running: str, served: str | None, clone: str | None) -> Check:
    """After a pull, the installed tool keeps running the old version until it's reinstalled. Compare what
    this process runs, what the agents' `deck-builder mcp` runs, and the clone doctor was started in."""
    target = clone or running
    behind = sorted({v for v in (running, served) if v and v != target})
    if not behind:
        return Check("install version", "ok", running)
    return Check("install version", "stale", f"the installed deck-builder is {', '.join(behind)}; the clone is "
                 f"{target}", "from the clone: uv tool install --reinstall . (add --editable for an editable install)")


def linked_agents(target: Path) -> Check:
    """`skills install` links each agent file; a release that adds an agent needs it run again."""
    from deck_builder.skills import AGENTS

    folder = target / "agents"
    linked = [a for a in AGENTS if (folder / a).exists()]
    if not linked:
        return Check("skills and agents", "optional", f"not linked into {target}",
                     "deck-builder skills install --yes, to use them in other projects")
    missing = [a.removesuffix(".md") for a in AGENTS if a not in linked]
    if missing:
        return Check("skills and agents", "stale", f"{', '.join(missing)} not linked into {target}",
                     "deck-builder skills install --yes")
    return Check("skills and agents", "ok", f"{len(linked)} agents linked into {target}")


def stale_kits(cfg: cfgmod.Config) -> Check:
    """Kits a different deck-builder generated, or whose brand.yaml changed since: they build, without the
    current generator's layouts and styling."""
    from deck_builder.brand import kit, registry

    brands, _ = registry.discover(cfg)
    stale = sorted(slug for slug, b in brands.items() if b.valid and kit.stale_issues(b))
    if not stale:
        return Check("brand kits", "ok", f"{len(brands)} found, none stale")
    return Check("brand kits", "stale", f"{', '.join(stale)} generated by another version or from an older "
                 "brand.yaml", "deck-builder brand init <slug> --force, after reading Upgrading in the README")


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
    mcp = agent_tools(cfg)
    checks.append(mcp)
    from deck_builder import __version__

    checks.append(install_version(__version__, mcp.version, clone_version(Path.cwd())))
    checks.append(linked_agents(Path.home() / ".claude"))
    if cfg.found:
        checks.append(stale_kits(cfg))
    return checks


def render_backend(checks: list[Check]) -> str | None:
    status = {c.name: c.status for c in checks}
    if status.get("poppler") != "ok":
        return None
    if status.get("libreoffice") == "ok":
        return "libreoffice"
    return "powerpoint" if status.get("powerpoint") == "unverified" else None
