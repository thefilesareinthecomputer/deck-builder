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
    # no deck-builder on PATH to probe, so this falls back to editable_install() for this process.
    monkeypatch.setattr("deck_builder.doctor.mcp_command", lambda: None)
    monkeypatch.setattr("deck_builder.doctor.editable_install", lambda: False)
    main(["--config", str(ws / "deck-builder.toml"), "doctor", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["editable_install"] is False

    main(["--config", str(ws / "deck-builder.toml"), "doctor"])
    assert "editable install" not in capsys.readouterr().out


def test_doctor_warns_from_the_mcp_servers_install_not_the_doctor_processs_own(ws, capsys, monkeypatch):
    """doctor itself can run from a regular install while `deck-builder` on PATH (the agents' MCP server) is
    this editable clone: the warning must reflect the process that actually serves the agents' tools."""
    monkeypatch.setattr("deck_builder.doctor.mcp_command", lambda: [sys.executable, "-m", "deck_builder"])
    monkeypatch.setattr("deck_builder.doctor.editable_install", lambda: False)  # the doctor process: not editable
    code = main(["--config", str(ws / "deck-builder.toml"), "doctor", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["editable_install"] is True  # the spawned deck-builder mcp process: this editable clone

    main(["--config", str(ws / "deck-builder.toml"), "doctor"])
    text = capsys.readouterr().out
    assert "warning" in text and "editable install" in text


# ---------------------------------------------------------------- after an update


def test_an_install_behind_the_clone_is_stale_with_the_reinstall_as_its_fix():
    assert doctor.install_version("0.2.0", "0.2.0", "0.2.0").status == "ok"
    assert doctor.install_version("0.2.0", None, None).status == "ok"  # not in a clone, no MCP server
    behind = doctor.install_version("0.2.0", "0.1.0", "0.2.0")  # the agents' tool wasn't reinstalled
    assert behind.status == "stale" and "0.1.0" in behind.detail and "--reinstall" in behind.fix
    assert doctor.install_version("0.1.0", "0.1.0", "0.2.0").status == "stale"  # pulled, not reinstalled


def test_the_clone_version_comes_from_its_own_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "deck-builder"\nversion = "9.9.9"\n')
    (tmp_path / "decks" / "q3").mkdir(parents=True)
    assert doctor.clone_version(tmp_path / "decks" / "q3") == "9.9.9"
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "other"\nversion = "1.0.0"\n')
    assert doctor.clone_version(tmp_path) is None


def test_agents_a_release_added_but_skills_install_hasnt_linked_are_stale(tmp_path):
    from deck_builder.skills import AGENTS

    assert doctor.linked_agents(tmp_path).status == "optional"  # never installed: nothing to update
    (tmp_path / "agents").mkdir()
    for name in AGENTS[:-1]:
        (tmp_path / "agents" / name).write_text("")
    stale = doctor.linked_agents(tmp_path)
    assert stale.status == "stale" and AGENTS[-1].removesuffix(".md") in stale.detail
    (tmp_path / "agents" / AGENTS[-1]).write_text("")
    assert doctor.linked_agents(tmp_path).status == "ok"


def test_doctor_names_kits_another_version_generated(ws, capsys):
    import yaml

    from deck_builder.brand.kit import inputs_sha

    kit = ws / "brands" / "stock"
    tokens = yaml.safe_load((kit / "tokens.yaml").read_text())
    meta = yaml.safe_load((kit / "brand.yaml").read_text())
    tokens["generated"] = {"by": "deck-builder 0.0.1", "inputs_sha256": inputs_sha(kit, meta)}
    (kit / "tokens.yaml").write_text(yaml.safe_dump(tokens))
    main(["--config", str(ws / "deck-builder.toml"), "doctor", "--json"])
    kits = next(c for c in json.loads(capsys.readouterr().out)["checks"] if c["name"] == "brand kits")
    assert kits["status"] == "stale" and "stock" in kits["detail"] and "--force" in kits["fix"]


FAKE_SERVER = """
import json, sys
for line in sys.stdin:
    m = json.loads(line)
    result = ({"serverInfo": {"name": "deck-builder", "version": "0.2.0", "missing": ["pygments"]}}
              if m["method"] == "initialize" else {"tools": []})
    print(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": result}), flush=True)
"""


def test_a_server_that_cant_import_a_dependency_is_missing_with_the_reinstall(ws, capsys, monkeypatch):
    monkeypatch.setattr("deck_builder.doctor.mcp_command", lambda: [sys.executable, "-c", FAKE_SERVER])
    check = agent_check(ws, capsys)
    assert check["status"] == "missing" and "can't import pygments" in check["detail"]
    assert "--reinstall" in check["fix"]


def test_a_server_that_crashes_at_start_says_why(ws, capsys, monkeypatch):
    crash = ("import sys; sys.modules['pygments'] = None; from deck_builder.cli import main; "
             "raise SystemExit(main(sys.argv[1:]))")
    monkeypatch.setattr("deck_builder.doctor.mcp_command", lambda: [sys.executable, "-c", crash])
    check = agent_check(ws, capsys)
    assert check["status"] == "missing" and "missing the 'pygments' package" in check["detail"]


def test_missing_imports_names_the_package(monkeypatch):
    monkeypatch.setitem(doctor.IMPORTS, "no-such-package", "no_such_module_for_this_test")
    assert doctor.missing_imports() == ["no-such-package"]


def _agent(folder, name, tools, command):
    (folder / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
    args = json.dumps(command[1:])
    (folder / ".claude" / "agents" / name).write_text(
        f"---\nname: {name[:-3]}\ntools: Read, {tools}\nmcpServers:\n  - deck-builder:\n      type: stdio\n"
        f"      command: {command[0]}\n      args: {args}\n---\n\nBody.\n", encoding="utf-8")


SERVER = ["deck-builder", "mcp"]  # as the agent files declare it


def test_the_agent_preflight_starts_each_declared_server_from_this_folder(ws, monkeypatch):
    monkeypatch.setattr("deck_builder.doctor.Path.home", lambda: ws / "home")
    monkeypatch.setattr("deck_builder.doctor.mcp_command", lambda: [sys.executable, "-m", "deck_builder"])
    _agent(ws, "deck-builder-agent.md", "mcp__deck-builder__check, mcp__deck-builder__docs", SERVER)
    _agent(ws, "deck-validator-agent.md", "mcp__deck-builder__check", SERVER)
    check = doctor.agent_preflight(ws)
    assert check.status == "ok" and check.detail.startswith("2 agents"), check
    _agent(ws, "deck-brand-agent.md", "mcp__deck-builder__brand_init, mcp__deck-builder__nope", SERVER)
    check = doctor.agent_preflight(ws)
    assert check.status == "missing" and "deck-brand-agent: the server doesn't serve nope" in check.detail


def test_the_agent_preflight_runs_only_deck_builder(ws, monkeypatch, tmp_path):
    monkeypatch.setattr("deck_builder.doctor.Path.home", lambda: ws / "home")
    marker = tmp_path / "ran"
    _agent(ws, "deck-builder-agent.md", "mcp__deck-builder__check", ["touch", str(marker)])
    check = doctor.agent_preflight(ws)
    assert check.status == "missing" and "declares `touch" in check.detail and not marker.exists()
    _agent(ws, "deck-builder-agent.md", "mcp__deck-builder__check", ["deck-builder", "mcp", "--config", "x.toml"])
    check = doctor.agent_preflight(ws)
    assert check.status == "missing" and "declares `deck-builder mcp --config x.toml`" in check.detail


def test_the_agent_preflight_fails_where_no_config_is_found(tmp_path, monkeypatch):
    """Claude Code starts a subagent's server in its own folder: with no deck-builder.toml at or above it, the
    server refuses to start and the agents have no tools."""
    monkeypatch.setattr("deck_builder.doctor.Path.home", lambda: tmp_path / "home")
    monkeypatch.delenv("DECK_BUILDER_CONFIG", raising=False)
    monkeypatch.setattr("deck_builder.config.USER_CONFIG", tmp_path / "none.toml")
    monkeypatch.setattr("deck_builder.doctor.mcp_command", lambda: [sys.executable, "-m", "deck_builder"])
    project = tmp_path / "project"
    _agent(project, "deck-builder-agent.md", "mcp__deck-builder__check", SERVER)
    check = doctor.agent_preflight(project)
    assert check.status == "missing" and "no deck-builder.toml here or above" in check.detail
    assert "deck-builder-agent:" in check.detail and "workspace folder" in check.fix


def test_a_dependency_missing_from_the_install_says_how_to_reinstall():
    """The update that broke an editable install: the code needs a package its environment lacks. The CLI
    names it and the reinstall instead of a traceback."""
    import subprocess

    proc = subprocess.run([sys.executable, "-c", "import sys; sys.modules['pygments'] = None; "
                           "from deck_builder.cli import main; raise SystemExit(main(['docs']))"],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 2
    assert "missing the 'pygments' package" in proc.stderr and "--reinstall" in proc.stderr
    assert "Traceback" not in proc.stderr
