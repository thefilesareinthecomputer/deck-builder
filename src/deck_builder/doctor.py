"""What this machine can do: build (Python only), render (PowerPoint or LibreOffice, plus poppler)."""
from __future__ import annotations

import importlib
import importlib.metadata as md
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from deck_builder import config as cfgmod
from deck_builder.qa import tools

# Each runtime dependency and the module it's imported as
IMPORTS = {"python-pptx": "pptx", "pyyaml": "yaml", "openpyxl": "openpyxl", "defusedxml": "defusedxml",
           "jsonschema": "jsonschema", "pillow": "PIL", "pygments": "pygments"}
PACKAGES = tuple(IMPORTS)
SERVER = "deck-builder"  # the MCP server name the agent files declare
MCP_HELLO = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
             {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]


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


def install_hint(reinstall: bool = False) -> str:
    clone = Path(__file__).resolve().parents[2]
    flags = "--editable --reinstall" if reinstall else "--editable"
    return f"uv tool install {flags} {clone if (clone / 'pyproject.toml').is_file() else '<clone>'}"


def missing_imports() -> list[str]:
    """The runtime dependencies this process can't import. The MCP server reports its own, so doctor sees
    what the install serving the agents lacks, such as a dependency added after it was installed."""
    out = []
    for pkg, module in IMPORTS.items():
        try:
            importlib.import_module(module)
        except ImportError:
            out.append(pkg)
    return out


def ask_server(cmd: list[str], cwd: Path | None = None) -> tuple[list[dict[str, Any]] | None, str]:
    """Start an MCP server, send initialize and tools/list, and return (its two replies, '') or (None, the
    last line it wrote to stderr, which says why it didn't answer)."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd,
                              input="".join(json.dumps(m) + "\n" for m in MCP_HELLO))
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"{type(e).__name__}: {e}"
    try:
        replies = [json.loads(ln) for ln in proc.stdout.splitlines()]
        replies[1]["result"]["tools"]
        return replies, ""
    except (ValueError, KeyError, IndexError, TypeError):
        lines = proc.stderr.strip().splitlines()
        return None, lines[-1] if lines else f"exit {proc.returncode}, no output"


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
    replies, why = ask_server([*cmd, "--config", str(cfg.path), "mcp"])
    if replies is None:
        return Check(name, "missing", f"`deck-builder mcp` didn't answer tools/list: {why}", install_hint(True))
    info = replies[0].get("result", {}).get("serverInfo", {})
    editable, version = bool(info.get("editable")), str(info.get("version") or "") or None
    if info.get("missing"):
        return Check(name, "missing", f"the installed deck-builder can't import {', '.join(info['missing'])}",
                     install_hint(True), editable=editable, version=version)
    return Check(name, "ok", f"`deck-builder mcp` answers with {len(replies[1]['result']['tools'])} tools",
                 editable=editable, version=version)


def _front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        return {}
    data = yaml.safe_load(text[4:text.index("\n---", 4)])
    return data if isinstance(data, dict) else {}


def _declared_server(meta: dict[str, Any]) -> list[str] | None:
    """The command an agent file's mcpServers entry starts the deck-builder server with."""
    servers = meta.get("mcpServers") or []
    for entry in servers if isinstance(servers, list) else [servers]:
        spec = entry.get(SERVER) if isinstance(entry, dict) else None
        if isinstance(spec, dict) and spec.get("command"):
            return [str(spec["command"]), *(str(a) for a in spec.get("args") or [])]
    return None


def agent_preflight(start: Path) -> Check:
    """Start the deck-builder server the way each agent file declares it, from this folder as Claude Code
    does for a subagent, and check it serves every MCP tool the agent's `tools:` line lists. A server that
    starts from the clone can still fail here, such as with no deck-builder.toml at or above this folder."""
    from deck_builder.skills import AGENTS

    name = "agent preflight"
    files = [next((p for p in (start / ".claude" / "agents" / a, Path.home() / ".claude" / "agents" / a)
                   if p.is_file()), None) for a in AGENTS]
    found = [f for f in files if f is not None]
    if not found:
        return Check(name, "optional", f"no agent files in {start / '.claude' / 'agents'} or ~/.claude/agents",
                     "deck-builder skills install --yes")
    served: dict[tuple[str, ...], tuple[set[str] | None, str]] = {}
    silent: dict[tuple[str, ...], list[str]] = {}  # agents whose declared server didn't answer
    problems, checked = [], 0
    for f in found:
        try:
            meta = _front_matter(f)
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as e:
            problems.append(f"{f.stem}: can't read its front matter ({type(e).__name__})")
            continue
        want = [t.split("__", 2)[2] for t in str(meta.get("tools") or "").replace(" ", "").split(",")
                if t.startswith(f"mcp__{SERVER}__")]
        if not want:
            continue  # the decomposer and the storyteller run no commands
        cmd = _declared_server(meta)
        if cmd is None:
            problems.append(f"{f.stem}: lists deck-builder tools but declares no {SERVER} MCP server")
            continue
        if cmd[:2] != [SERVER, "mcp"] or (exe := mcp_command()) is None:
            # only ever run deck-builder itself: an agent file in this folder is not trusted to name a command
            problems.append(f"{f.stem}: declares `{' '.join(cmd)}`; the agents' server is `{SERVER} mcp` on PATH")
            continue
        key = tuple(cmd)
        if key not in served:
            replies, why = ask_server([*exe, *cmd[1:]], cwd=start)
            served[key] = ({str(t.get("name")) for t in replies[1]["result"]["tools"]} if replies else None, why)
        tools_, why = served[key]
        checked += 1
        if tools_ is None:
            silent.setdefault(key, []).append(f.stem)
        elif lacking := [t for t in want if t not in tools_]:
            problems.append(f"{f.stem}: the server doesn't serve {', '.join(lacking)}")
    problems += [f"{', '.join(agents)}: `{' '.join(key)}` didn't answer from {start}: {served[key][1]}"
                 for key, agents in silent.items()]
    if problems:
        return Check(name, "missing", "; ".join(problems),
                     "start Claude Code in the workspace folder (where deck-builder.toml is), or run "
                     f"`{install_hint(True)}` when the server can't import a package")
    return Check(name, "ok", f"{checked} agents: the server each declares starts here and serves every tool it lists")


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
                 "brand.yaml", "with the brand owner's OK, deck-builder brand init <slug> --force; it replaces "
                 "tuned budgets and template edits, keeping the old kit in its backups/ folder. See Updating "
                 "in the README")


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
    if mcp.status == "ok":
        checks.append(agent_preflight(Path.cwd()))
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
