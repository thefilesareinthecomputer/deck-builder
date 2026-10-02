"""`deck-builder mcp`: the engine as MCP tools over stdio, for agents that have no shell.

The transport is MCP's stdio framing (newline-delimited JSON-RPC 2.0), written here by hand so the
engine keeps no network library. Each tool builds the argv the CLI would get, runs it through the
CLI's own parser and handler, and returns the JSON that `--json` prints, so the two surfaces can't
drift apart. Paths are confined before anything runs: decks, data and outputs must resolve inside
the workspace root (the config file's folder), brand writes inside a configured brand_paths entry,
and brand reads inside either. Anything else is refused. With the server missing, an agent that
relies on it can run nothing.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

import jsonschema

from deck_builder import __version__
from deck_builder import config as cfgmod
from deck_builder.errors import EXIT_ENV, EnvError

PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")  # newest first
ROOT, BRAND_READ, BRAND_WRITE, SLUG_OR_ROOT = "root", "brand-read", "brand-write", "slug-or-root"
SLUG_PATTERN = "^[a-z0-9][a-z0-9-]*$"

TEXT: dict[str, Any] = {"type": "string", "minLength": 1}
FLAG: dict[str, Any] = {"type": "boolean"}
SLUG: dict[str, Any] = {"type": "string", "pattern": SLUG_PATTERN}


@dataclass(frozen=True)
class Arg:
    name: str
    schema: dict[str, Any]
    flag: str | None = None  # the CLI option; None for a positional argument
    path: str | None = None  # where a path may point: ROOT, BRAND_READ, BRAND_WRITE or SLUG_OR_ROOT
    required: bool = False
    about: str = ""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    command: tuple[str, ...]  # the CLI words before the arguments
    args: tuple[Arg, ...] = ()

    def schema(self) -> dict[str, Any]:
        props = {a.name: {**a.schema, **({"description": a.about} if a.about else {})} for a in self.args}
        return {"type": "object", "properties": props, "required": [a.name for a in self.args if a.required],
                "additionalProperties": False}


TOOLS = {t.name: t for t in (
    Tool("check", "Validate a deck (deck.md, deck.xlsx or deck.csv, or the folder holding it). With render, also "
         "build, render and measure; the result lists flagged_slides, render_dir and contact_sheets.", ("check",), (
             Arg("deck", TEXT, path=ROOT, required=True, about="the deck file or its folder, inside the workspace"),
             Arg("brand", SLUG, "--brand", about="brand slug, overriding the deck's brand:"),
             Arg("render", FLAG, "--render"))),
    Tool("build", "Build a deck into a .pptx and its manifest. With data, build one deck per row of a CSV or "
         "XLSX file.", ("build",), (
             Arg("deck", TEXT, path=ROOT, required=True),
             Arg("brand", SLUG, "--brand"),
             Arg("output", TEXT, "--output", ROOT, about="a .pptx path or a folder, inside the workspace"),
             Arg("data", TEXT, "--data", ROOT),
             Arg("name", {"type": "string", "pattern": r"^(?!.*\.\.)[^/\\]+\.pptx$"}, "--name",
                 about="bulk file name pattern, such as {{client}}.pptx"))),
    Tool("render", "Render a .pptx the engine built (its manifest must sit beside it) with the configured backend: "
         "PDF, slide PNGs, contact sheets and the slides to look at.", ("render",), (
             Arg("pptx", TEXT, path=ROOT, required=True),
             Arg("slides", {"type": "string", "pattern": "^[0-9]+(,[0-9]+)*$"}, "--slides"),
             Arg("dpi", {"type": "integer", "minimum": 48, "maximum": 300}, "--dpi"))),
    Tool("convert", "Convert a deck between .md, .xlsx and .csv without losing anything.", ("convert",), (
        Arg("input", TEXT, path=ROOT, required=True),
        Arg("output", TEXT, path=ROOT, required=True, about="its extension picks the format"),
        Arg("force", FLAG, "--force"))),
    Tool("import", "Turn an existing .pptx back into deck.md, its images and import-report.md, on an existing "
         "brand or a brand adopted from the file. Give exactly one of brand and adopt.", ("import",), (
             Arg("pptx", TEXT, path=ROOT, required=True),
             Arg("out", TEXT, path=ROOT, required=True),
             Arg("brand", SLUG, "--brand"),
             Arg("adopt", SLUG, "--adopt"),
             Arg("force", FLAG, "--force"))),
    Tool("brand_list", "List the brands under brand_paths.", ("brand", "list")),
    Tool("brand_show", "A brand's layouts, fields, kinds and budgets, palette names and asset ids.",
         ("brand", "show"), (Arg("slug", SLUG, required=True),)),
    Tool("brand_check", "Check a brand kit: schemas, template mapping, assets and color contrast.",
         ("brand", "check"), (Arg("slug", SLUG, required=True),)),
    Tool("brand_init", "Generate a brand kit (template and tokens.yaml) from a brand.yaml.", ("brand", "init"), (
        Arg("slug", SLUG, required=True),
        Arg("from", TEXT, "--from", BRAND_READ, required=True, about="the brand.yaml to generate from"),
        Arg("out", TEXT, "--out", BRAND_WRITE, about="a brand_paths folder (default: the first)"),
        Arg("force", FLAG, "--force"))),
    Tool("brand_adopt", "Wrap an existing .potx or .pptx template as a brand kit.", ("brand", "adopt"), (
        Arg("slug", SLUG, required=True),
        Arg("template", TEXT, "--template", BRAND_READ, required=True),
        Arg("out", TEXT, "--out", BRAND_WRITE),
        Arg("force", FLAG, "--force"))),
    Tool("brand_add_asset", "Copy a PNG into a brand kit as a logo or an icon.", ("brand", "add-asset"), (
        Arg("slug", SLUG, required=True),
        Arg("file", TEXT, path=BRAND_READ, required=True),
        Arg("as", {"type": "string", "pattern": "^(logo|icon)/[a-z0-9][a-z0-9-]*$"}, "--as", required=True,
            about="logo/<id> or icon/<id>"),
        Arg("force", FLAG, "--force"))),
    Tool("inspect", "A template's layouts, placeholders and theme.", ("inspect",), (
        Arg("template", TEXT, path=BRAND_READ, required=True),
        Arg("yaml", FLAG, "--yaml", about="also a starter layouts block for tokens.yaml"))),
    Tool("assets", "Inventory a brand's assets (by slug) or a deck's (by path).", ("assets",), (
        Arg("target", TEXT, path=SLUG_OR_ROOT, required=True),)),
    Tool("docs", "A reference topic, such as deck-md, workbook, brand-yaml, tokens-yaml, workflow or codes; "
         "no topic lists them.", ("docs",), (Arg("topic", {"type": "string", "pattern": "^[a-z-]+$"}),)),
    Tool("explain", "The cause and fix for one issue code.", ("explain",), (
        Arg("code", {"type": "string", "pattern": "^[A-Za-z_]+$"}, required=True),)),
    Tool("doctor", "Dependencies, render backends and what this machine can do.", ("doctor",)),
)}


class Refused(Exception):
    """A tool call this server won't run, with the reason the agent sees."""


class Server:
    def __init__(self, cfg: cfgmod.Config) -> None:
        assert cfg.path is not None
        self.cfg = cfg
        self.root = cfg.path.parent.resolve()
        self.brands = [p.resolve() for p in cfg.brand_paths]
        from deck_builder import cli  # the CLI's own parser and handlers

        self.cli = cli
        self.parser, self.handlers = cli.build_parser()

    # -- confinement

    def _path(self, arg: Arg, value: str) -> str:
        if arg.path == SLUG_OR_ROOT and jsonschema.Draft202012Validator(SLUG).is_valid(value):
            return value  # a brand slug, not a path
        p = Path(value)
        full = (p if p.is_absolute() else self.root / p).resolve()  # follows symlinks
        allowed = {ROOT: [self.root], SLUG_OR_ROOT: [self.root], BRAND_WRITE: self.brands,
                   BRAND_READ: [self.root, *self.brands]}[str(arg.path)]
        if not any(full.is_relative_to(a) for a in allowed):
            where = {ROOT: "the workspace", SLUG_OR_ROOT: "the workspace", BRAND_WRITE: "a brand_paths folder",
                     BRAND_READ: "the workspace or a brand_paths folder"}[str(arg.path)]
            raise Refused(f"{arg.name}: {value!r} is outside {where} ({', '.join(map(str, allowed))})")
        return str(full)

    @staticmethod
    def _engine_built(pptx: str) -> None:
        """Agents render only what the engine built: LibreOffice never opens a file an agent wrote by hand."""
        p = Path(pptx)
        manifest = p.with_name(p.stem + ".manifest.json")
        try:
            recorded = json.loads(manifest.read_text(encoding="utf-8"))["output"]["sha256"]
        except (OSError, ValueError, KeyError, TypeError):
            raise Refused(f"{p.name} has no build manifest beside it; render takes decks the engine built") from None
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != recorded:
            raise Refused(f"{p.name} isn't the file its manifest records; rebuild it, then render")

    def argv(self, tool: Tool, arguments: dict[str, Any]) -> list[str]:
        errors = sorted(jsonschema.Draft202012Validator(tool.schema()).iter_errors(arguments), key=str)
        if errors:
            raise Refused("; ".join(e.message for e in errors))
        if tool.name == "render":
            self._engine_built(self._path(tool.args[0], arguments["pptx"]))
        out = ["--config", str(self.cfg.path), *tool.command]
        for arg in tool.args:
            if arg.name not in arguments:
                continue
            value = arguments[arg.name]
            if isinstance(value, bool):
                out += [arg.flag] if value and arg.flag else []
                continue
            text = self._path(arg, value) if arg.path else str(value)
            out += [arg.flag, text] if arg.flag else [text]
        return out

    # -- tools

    def call(self, tool: Tool, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            argv = self.argv(tool, arguments)
        except Refused as e:
            return _text(f"refused: {e}", error=True)
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                args = self.parser.parse_args(argv)
        except SystemExit:
            return _text(f"refused: {err.getvalue().strip().splitlines()[-1] if err.getvalue() else 'bad arguments'}",
                         error=True)
        try:
            with contextlib.redirect_stdout(sys.stderr):  # stdout belongs to the protocol
                result = self.cli.run(self.handlers[args.command], args)
        except Exception as e:  # an engine bug: report it, keep serving
            return _text(f"internal error: {type(e).__name__}: {e}", error=True)
        return _text(json.dumps(result.as_dict(), default=str), error=result.exit_code != 0)

    # -- JSON-RPC

    def handle(self, line: str) -> dict[str, Any] | None:
        try:
            msg = json.loads(line)
        except ValueError:
            return _error(None, -32700, "parse error")
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
            return _error(msg.get("id") if isinstance(msg, dict) else None, -32600, "invalid request")
        if "id" not in msg:
            return None  # a notification, such as notifications/initialized: nothing to answer
        mid, method, params = msg["id"], msg["method"], msg.get("params") or {}
        if not isinstance(params, dict):
            return _error(mid, -32602, "params must be an object")
        if method == "initialize":
            asked = params.get("protocolVersion")
            return _result(mid, {
                "protocolVersion": asked if asked in PROTOCOLS else PROTOCOLS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "deck-builder", "version": __version__},
                "instructions": f"deck-builder tools, confined to the workspace at {self.root}. Paths are "
                                "relative to it. Start with brand_show and docs deck-md.",
            })
        if method == "ping":
            return _result(mid, {})
        if method == "tools/list":
            return _result(mid, {"tools": [{"name": t.name, "description": t.description, "inputSchema": t.schema()}
                                           for t in TOOLS.values()]})
        if method == "tools/call":
            tool = TOOLS.get(str(params.get("name")))
            arguments = params.get("arguments") or {}
            if tool is None:
                return _error(mid, -32602, f"unknown tool {params.get('name')!r}")
            if not isinstance(arguments, dict):
                return _error(mid, -32602, "arguments must be an object")
            return _result(mid, self.call(tool, arguments))
        return _error(mid, -32601, f"unknown method {method!r}")


def _text(text: str, error: bool) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": error}


def _result(mid: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _error(mid: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def serve(config: str | None, stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
    """Answer one JSON-RPC message per line until stdin closes. Refuses to start without a config file."""
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    try:
        cfg = cfgmod.load(config)
    except EnvError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ENV
    if not cfg.found:
        print("error: no deck-builder.toml here or above; the MCP server confines tools to that file's folder, "
              "so run `deck-builder init` first", file=sys.stderr)
        return EXIT_ENV
    server = Server(cfg)
    for line in stdin:
        if not line.strip():
            continue
        try:
            reply = server.handle(line)
        except Exception as e:  # never let one message end the session
            reply = _error(None, -32603, f"internal error: {type(e).__name__}")
        if reply is not None:
            stdout.write(json.dumps(reply, default=str) + "\n")
            stdout.flush()
    return 0
