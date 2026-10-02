"""`deck-builder mcp`: the engine as MCP tools for agents without a shell, confined to the workspace."""
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from pptx import Presentation
from test_check import GOOD

from conftest import write_deck
from deck_builder import config as cfgmod
from deck_builder import mcp
from deck_builder.qa import tools as qa_tools

DEMO = Path(__file__).resolve().parents[1] / "fixtures" / "demo-brands"


@pytest.fixture
def server(ws):
    return mcp.Server(cfgmod.load(str(ws / "deck-builder.toml")))


@pytest.fixture
def outside(tmp_path_factory):
    """A folder outside the workspace, with a deck, a PNG and a template in it."""
    d = tmp_path_factory.mktemp("outside")
    (d / "deck.md").write_text(GOOD.lstrip("\n"))
    Image.new("RGBA", (64, 64), (0, 0, 0, 255)).save(d / "logo.png")
    Presentation().save(str(d / "template.pptx"))
    return d


def rpc(server, method, params=None, mid=1):
    msg = {"jsonrpc": "2.0", "id": mid, "method": method}
    if params is not None:
        msg["params"] = params
    return server.handle(json.dumps(msg))


def call(server, tool, **arguments):
    """A tool call -> (isError, the text: the CLI's --json object when it parses, else the message)."""
    reply = rpc(server, "tools/call", {"name": tool, "arguments": arguments})
    result = reply["result"]
    text = result["content"][0]["text"]
    try:
        return result["isError"], json.loads(text)
    except ValueError:
        return result["isError"], text


# ---------------------------------------------------------------- protocol


def test_initialize_answers_with_the_protocol_and_the_tools_capability(server):
    reply = rpc(server, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                       "clientInfo": {"name": "test", "version": "0"}})
    r = reply["result"]
    assert reply["id"] == 1 and reply["jsonrpc"] == "2.0"
    assert r["protocolVersion"] == "2025-03-26"
    assert r["capabilities"] == {"tools": {"listChanged": False}}
    assert r["serverInfo"]["name"] == "deck-builder"
    assert rpc(server, "initialize", {"protocolVersion": "1999-01-01"})["result"]["protocolVersion"] == "2025-06-18"


def test_tools_list_names_every_tool_with_a_closed_schema(server):
    tools = rpc(server, "tools/list")["result"]["tools"]
    assert {t["name"] for t in tools} == {
        "check", "build", "render", "convert", "import", "brand_list", "brand_show", "brand_check", "brand_init",
        "brand_adopt", "brand_add_asset", "inspect", "assets", "docs", "explain", "doctor"}
    for t in tools:
        assert t["description"]
        assert t["inputSchema"]["type"] == "object"
        assert t["inputSchema"]["additionalProperties"] is False


def test_nothing_that_installs_or_initializes_is_exposed(server):
    names = {t["name"] for t in rpc(server, "tools/list")["result"]["tools"]}
    assert not names & {"init", "skills", "skills_install", "mcp"}
    render = mcp.TOOLS["render"].schema()["properties"]
    assert "backend" not in render  # renders use the configured backend only


def test_every_tool_parameter_and_cli_argument_says_what_it_takes():
    from deck_builder.cli import build_parser

    for tool in mcp.TOOLS.values():
        for name, prop in tool.schema()["properties"].items():
            assert prop.get("description"), f"{tool.name}.{name}"
    ap, _ = build_parser()
    commands = next(a for a in ap._actions if a.dest == "command").choices
    for cmd, p in commands.items():
        for a in p._actions:
            assert a.dest in ("help", "json") or a.help, f"{cmd} {a.option_strings or a.dest}"


def test_ping_and_notifications(server):
    assert rpc(server, "ping")["result"] == {}
    assert server.handle(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})) is None


@pytest.mark.parametrize("line, code", [
    ("{not json", -32700),
    ("[1, 2]", -32600),
    ('{"jsonrpc": "2.0", "id": 3}', -32600),
    ('{"jsonrpc": "1.0", "id": 3, "method": "ping"}', -32600),
    ('{"jsonrpc": "2.0", "id": 3, "method": "resources/list"}', -32601),
    ('{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": [1]}', -32602),
    ('{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "nope"}}', -32602),
    ('{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "check", "arguments": "x"}}', -32602),
])
def test_malformed_messages_get_an_error_never_a_crash(server, line, code):
    assert server.handle(line)["error"]["code"] == code


def test_serve_answers_line_by_line_and_survives_garbage(ws):
    lines = [
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        "garbage",
        "",
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "explain", "arguments": {"code": "PARSE"}}}),
    ]
    out = io.StringIO()
    assert mcp.serve(str(ws / "deck-builder.toml"), io.StringIO("\n".join(lines) + "\n"), out) == 0
    replies = [json.loads(ln) for ln in out.getvalue().splitlines()]
    assert [r.get("id") for r in replies] == [1, None, 2]
    assert replies[1]["error"]["code"] == -32700
    assert json.loads(replies[2]["result"]["content"][0]["text"])["code"] == "PARSE"


def test_serve_refuses_to_start_without_a_config(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DECK_BUILDER_CONFIG", raising=False)
    monkeypatch.setattr("deck_builder.config.USER_CONFIG", tmp_path / "none.toml")
    assert mcp.serve(None, io.StringIO(""), io.StringIO()) == 2
    assert "deck-builder init" in capsys.readouterr().err


def test_the_cli_starts_the_server_over_stdio(ws):
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
    proc = subprocess.run([sys.executable, "-m", "deck_builder", "--config", str(ws / "deck-builder.toml"), "mcp"],
                          input="".join(json.dumps(m) + "\n" for m in msgs), capture_output=True, text=True,
                          timeout=60)
    assert proc.returncode == 0, proc.stderr
    replies = [json.loads(ln) for ln in proc.stdout.splitlines()]  # stdout holds protocol messages only
    assert [r["id"] for r in replies] == [1, 2]
    assert len(replies[1]["result"]["tools"]) == len(mcp.TOOLS)


# ---------------------------------------------------------------- tools, on the fixtures


def test_check_build_convert_and_import(server, ws):
    write_deck(ws, GOOD)
    err, out = call(server, "check", deck="decks")
    assert not err and out["ok"] and out["slides"] == 7
    err, out = call(server, "build", deck="decks/deck.md", output="out/q3.pptx")
    assert not err and Path(out["output"]) == (ws / "out" / "q3.pptx").resolve()
    err, out = call(server, "convert", input="decks/deck.md", output="decks/deck.xlsx")
    assert not err and (ws / "decks" / "deck.xlsx").is_file()
    err, out = call(server, "import", pptx="out/q3.pptx", out="imported", brand="stock")
    assert not err and (ws / "imported" / "deck.md").is_file()


def test_a_deck_with_issues_is_an_error_result_with_the_issues(server, ws):
    write_deck(ws, "## A\nlayout: nope\n")
    err, out = call(server, "check", deck="decks/deck.md")
    assert err and out["issues"][0]["code"] == "UNKNOWN_LAYOUT"


@pytest.mark.skipif(qa_tools.soffice() is None or bool(qa_tools.poppler_missing()), reason="needs LibreOffice")
def test_render(server, ws):
    write_deck(ws, GOOD)
    assert not call(server, "build", deck="decks/deck.md")[0]
    err, out = call(server, "render", pptx="out/decks.pptx", slides="1")
    assert not err and Path(out["contact_sheets"][0]).is_file()


def test_brand_tools(server, ws):
    assert [b["slug"] for b in call(server, "brand_list")[1]["brands"]] == ["stock"]
    assert "layouts" in call(server, "brand_show", slug="stock")[1]
    assert call(server, "brand_check", slug="stock")[1]["ok"]
    shutil.copytree(DEMO / "brands" / "briarfield-paper", ws / "incoming" / "briarfield-paper")
    err, out = call(server, "brand_init", slug="briarfield-paper", **{"from": "incoming/briarfield-paper/brand.yaml"})
    assert not err, out
    Presentation().save(str(ws / "client.pptx"))
    err, out = call(server, "brand_adopt", slug="client", template="client.pptx")
    assert not err, out
    assert "layouts" in call(server, "inspect", template="client.pptx")[1]
    Image.new("RGBA", (64, 64), (0, 0, 0, 255)).save(ws / "star.png")
    err, out = call(server, "brand_add_asset", slug="stock", file="star.png", **{"as": "icon/star"})
    assert not err and out["ref"] == "brand:icon/star"
    assert (ws / "brands" / "stock" / "assets" / "icons" / "star.png").is_file()


def test_assets_docs_explain_doctor(server, ws):
    write_deck(ws, GOOD)
    assert call(server, "assets", target="stock")[1]["brand"] == "stock"
    assert call(server, "assets", target="decks/deck.md")[1]["brand"] == "stock"
    assert "deck-md" in call(server, "docs")[1]["topics"]
    assert "The deck.md format" in call(server, "docs", topic="deck-md")[1]["text"]
    assert call(server, "explain", code="PARSE")[1]["code"] == "PARSE"
    assert "checks" in call(server, "doctor")[1] or call(server, "doctor")[1]["command"] == "doctor"


# ---------------------------------------------------------------- confinement: every refusal


def refused(server, tool, **arguments):
    err, text = call(server, tool, **arguments)
    assert err and isinstance(text, str) and text.startswith("refused:"), text
    return text


def test_a_deck_outside_the_workspace_is_refused(server, outside):
    assert "is outside the workspace" in refused(server, "check", deck=str(outside / "deck.md"))


def test_dot_dot_out_of_the_workspace_is_refused(server, ws, outside):
    rel = Path("..") / outside.name / "deck.md"
    refused(server, "check", deck=str(rel))


def test_a_symlink_out_of_the_workspace_is_refused(server, ws, outside):
    (ws / "decks" / "linked").symlink_to(outside)
    refused(server, "check", deck="decks/linked/deck.md")


@pytest.mark.parametrize("rel", [".claude/settings.json", ".git/config", "src/deck_builder/cli.py"])
def test_the_clones_own_folders_are_refused_even_inside_the_workspace(server, ws, rel):
    p = ws / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x", encoding="utf-8")
    assert "part of this clone's own files" in refused(server, "check", deck=str(p))


@pytest.mark.parametrize("name", ["AGENTS.md", "CLAUDE.md", "deck-builder.toml"])
def test_the_clones_own_filenames_are_refused_even_inside_the_workspace(server, ws, name):
    p = ws / "decks" / name
    p.write_text("x", encoding="utf-8")
    assert "part of this clone's own files" in refused(server, "check", deck=str(p))


def test_example_decks_from_init_check_and_build_through_mcp(tmp_path):
    """The clone layout: deck-builder.toml beside src/, .claude/ and AGENTS.md, workspace a subfolder."""
    from deck_builder.cli import main as cli_main

    (tmp_path / "src" / "deck_builder").mkdir(parents=True)
    (tmp_path / "src" / "deck_builder" / "cli.py").write_text("# engine source\n", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# repo instructions\n", encoding="utf-8")
    assert cli_main(["init", "--dir", str(tmp_path)]) == 0

    srv = mcp.Server(cfgmod.load(str(tmp_path / "deck-builder.toml")))
    err, out = call(srv, "check", deck="workspace/decks/quarterly-review/deck.md")
    assert not err and out["ok"], out
    err, out = call(srv, "build", deck="workspace/decks/quarterly-review/deck.md")
    assert not err, out

    assert "part of this clone's own files" in refused(srv, "check", deck=str(tmp_path / "src" / "deck_builder" /
                                                                               "cli.py"))
    assert "part of this clone's own files" in refused(srv, "check",
                                                        deck=str(tmp_path / ".claude" / "settings.json"))
    assert "part of this clone's own files" in refused(srv, "check", deck=str(tmp_path / "AGENTS.md"))


@pytest.mark.parametrize("name, args", [
    ("build", {"deck": "decks/deck.md", "output": "{outside}/x.pptx"}),
    ("build", {"deck": "decks/deck.md", "data": "{outside}/rows.csv"}),
    ("convert", {"input": "decks/deck.md", "output": "{outside}/deck.md"}),
    ("convert", {"input": "{outside}/deck.md", "output": "decks/x.md"}),
    ("import", {"pptx": "{outside}/x.pptx", "out": "imported", "brand": "stock"}),
    ("import", {"pptx": "out/x.pptx", "out": "{outside}/imp", "brand": "stock"}),
    ("render", {"pptx": "{outside}/x.pptx"}),
    ("assets", {"target": "{outside}/deck.md"}),
    ("inspect", {"template": "{outside}/template.pptx"}),
    ("brand_adopt", {"slug": "evil", "template": "{outside}/template.pptx"}),
    ("brand_init", {"slug": "evil", "from": "{outside}/brand.yaml"}),
    ("brand_add_asset", {"slug": "stock", "file": "{outside}/logo.png", "as": "logo/primary"}),
])
def test_every_path_argument_outside_its_area_is_refused(server, ws, outside, name, args):
    write_deck(ws, GOOD)
    args = {k: v.format(outside=outside) for k, v in args.items()}
    refused(server, name, **args)


@pytest.mark.parametrize("name, args", [
    ("brand_init", {"slug": "x", "from": "brand.yaml", "out": "decks"}),
    ("brand_adopt", {"slug": "x", "template": "client.pptx", "out": "decks"}),
])
def test_brand_writes_outside_brand_paths_are_refused(server, ws, name, args):
    assert "outside a brand_paths folder" in refused(server, name, **args)


@pytest.mark.parametrize("name, args, why", [
    ("check", {"deck": "decks", "shell": "ls"}, "Additional properties"),
    ("check", {}, "'deck' is a required property"),
    ("check", {"deck": "decks", "render": "yes"}, "is not of type 'boolean'"),
    ("brand_show", {"slug": "../stock"}, "does not match"),
    ("build", {"deck": "decks", "name": "../{{x}}.pptx"}, "does not match"),
    ("render", {"pptx": "out/x.pptx", "slides": "1; rm -rf /"}, "does not match"),
    ("import", {"pptx": "out/x.pptx", "out": "imp", "brand": "stock", "adopt": "x"}, "not allowed with"),
])
def test_arguments_that_dont_fit_the_schema_or_the_cli_are_refused(server, ws, name, args, why):
    assert why in refused(server, name, **args)


def test_render_takes_only_files_the_engine_built(server, ws):
    write_deck(ws, GOOD)
    assert not call(server, "build", deck="decks/deck.md")[0]
    (ws / "out" / "planted.pptx").write_text("<office:document>macros here</office:document>")
    assert "has no build manifest beside it" in refused(server, "render", pptx="out/planted.pptx")
    built = ws / "out" / "decks.pptx"
    built.write_bytes(built.read_bytes() + b"tampered")
    assert "isn't the file its manifest records" in refused(server, "render", pptx="out/decks.pptx")


def test_help_text_never_reaches_the_protocol_stream(server, capsys):
    refused(server, "docs", topic="-h")  # the schema refuses a topic starting with -
    capsys.readouterr()
    call(server, "explain", code="PARSE")
    server.call(mcp.TOOLS["docs"], {"topic": "codes"})
    assert capsys.readouterr().out == ""  # handlers and argparse write nothing to stdout


def test_a_path_with_a_nul_byte_is_refused_not_a_crash(server):
    assert "isn't a usable path" in refused(server, "check", deck="decks/\x00deck.md")


def test_a_refused_call_runs_nothing(server, ws, outside):
    write_deck(ws, GOOD)
    refused(server, "convert", input="decks/deck.md", output=str(outside / "deck.md"), force=True)
    assert (outside / "deck.md").read_text() == GOOD.lstrip("\n")  # untouched


# ---------------------------------------------------------------- brand add-asset (CLI)


def test_add_asset_copies_a_png_logo_and_says_how_to_declare_it(ws, capsys):
    from conftest import cli_json

    Image.new("RGBA", (300, 100), (0, 0, 0, 255)).save(ws / "mono.png")
    code, out = cli_json(ws, "brand", "add-asset", "stock", str(ws / "mono.png"), "--as", "logo/mono", capsys=capsys)
    assert code == 0, out
    assert (ws / "brands" / "stock" / "assets" / "mono.png").is_file()
    assert out["ref"] == "brand:logo/mono"
    code, out = cli_json(ws, "brand", "add-asset", "stock", str(ws / "mono.png"), "--as", "logo/mono", capsys=capsys)
    assert code == 2 and "pass --force" in out["error"]
    from deck_builder.cli import main

    main(["--config", str(ws / "deck-builder.toml"), "brand", "add-asset", "stock", str(ws / "mono.png"), "--as",
          "logo/mono", "--force"])
    assert "add `mono: assets/mono.png` under logos: in brand.yaml" in capsys.readouterr().out


@pytest.mark.parametrize("make, as_, why", [
    (lambda p: Image.new("RGB", (10, 10)).save(p, "JPEG"), "logo/x", "isn't a PNG"),
    (lambda p: p.write_text("not an image"), "logo/x", "isn't a PNG"),
    (lambda p: Image.new("RGBA", (10, 10)).save(p, "PNG"), "logo/../x", "--as logo/<id> or icon/<id>"),
    (lambda p: Image.new("RGBA", (10, 10)).save(p, "PNG"), "font/x", "--as logo/<id> or icon/<id>"),
])
def test_add_asset_refuses_what_isnt_a_png_logo_or_icon(ws, capsys, make, as_, why):
    from conftest import cli_json

    make(ws / "thing.png")
    code, out = cli_json(ws, "brand", "add-asset", "stock", str(ws / "thing.png"), "--as", as_, capsys=capsys)
    assert code == 2 and why in out["error"]
