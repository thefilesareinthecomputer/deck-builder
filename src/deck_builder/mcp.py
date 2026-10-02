"""`deck-builder mcp`: the engine as MCP tools over stdio, for agents that have no shell.

The transport is MCP's stdio framing (newline-delimited JSON-RPC 2.0), written here by hand so the
engine keeps no network library. Each tool builds the argv the CLI would get, runs it through the
CLI's own parser and handler, and returns the JSON that `--json` prints, so the two surfaces can't
drift apart. Paths are confined before anything runs: decks, data and outputs must resolve inside
the workspace (relative paths resolve against the config file's folder first, then the result must
land inside the workspace), brand writes inside a configured brand_paths entry, and brand reads
inside either. This clone's own .claude, .git and src folders, and files named AGENTS.md, CLAUDE.md
or deck-builder.toml, are refused regardless. Anything else outside the allowed areas is refused
too. With the server missing, an agent that relies on it can run nothing.
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

from deck_builder import __version__, confine
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


# Arguments several tools share, so the same name always means the same thing.
DECK = Arg("deck", TEXT, path=ROOT, required=True,
           about="the deck file (deck.md, deck.xlsx or deck.csv) or its folder, e.g. workspace/decks/q3")
BRAND = Arg("brand", SLUG, "--brand", about="a brand slug (see brand_list), overriding the deck's own brand:")
SLUG_ARG = Arg("slug", SLUG, required=True, about="the brand's slug, e.g. neutral (see brand_list)")
FORCE = Arg("force", FLAG, "--force", about="replace what's already there (default false)")

# Every tool returns the CLI's --json object as text: "ok", "issues" (each with code, severity, message,
# slide, field) and command-specific keys. isError is true when the command exits 1 (issues to fix) or
# 2 (a usage or environment problem, with "error" saying what).
TOOLS = {t.name: t for t in (
    Tool("check", "Validate a deck against its brand: layouts, fields, budgets, assets. Returns ok and issues; fix "
         "each issue by its code (explain gives the fix). With render: true it also builds, renders and measures, "
         "and adds output, flagged_slides, render_dir and contact_sheets: read the PNGs of flagged slides only.",
         ("check",), (DECK, BRAND, Arg("render", FLAG, "--render", about="also build, render and measure"))),
    Tool("build", "Build a deck into a .pptx plus its manifest; returns output, manifest and slides. With data, "
         "builds one deck per row of a CSV or XLSX file into the output folder.", ("build",), (
             DECK, BRAND,
             Arg("output", TEXT, "--output", ROOT, about="a .pptx path or a folder, inside the workspace "
                 "(default: workspace/out/<deck folder name>.pptx)"),
             Arg("data", TEXT, "--data", ROOT, about="bulk mode: a CSV or XLSX file, one deck per row"),
             Arg("name", {"type": "string", "pattern": r"^(?!.*\.\.)[^/\\]+\.pptx$"}, "--name",
                 about="bulk mode file name pattern, e.g. {{client}}.pptx"))),
    Tool("render", "Render a .pptx that build made (its .manifest.json must sit beside it) with the configured "
         "backend. Returns render_dir, the slide PNGs, contact_sheets and flagged_slides.", ("render",), (
             Arg("pptx", TEXT, path=ROOT, required=True, about="the built .pptx, e.g. workspace/out/q3.pptx"),
             Arg("slides", {"type": "string", "pattern": "^[0-9]+(,[0-9]+)*$"}, "--slides",
                 about="only these slide numbers, e.g. 3,7"),
             Arg("dpi", {"type": "integer", "minimum": 48, "maximum": 300}, "--dpi",
                 about="PNG resolution (default 96, which gives 1280 px wide slides)"))),
    Tool("convert", "Convert a deck between .md, .xlsx and .csv without losing anything; refuses with "
         "CONVERT_LOSSY when the target can't hold the content.", ("convert",), (
             Arg("input", TEXT, path=ROOT, required=True, about="the deck to convert"),
             Arg("output", TEXT, path=ROOT, required=True, about="the file to write; its extension picks the format"),
             FORCE)),
    Tool("import", "Turn an existing .pptx back into out/deck.md, out/assets/ and out/import-report.md. Give "
         "exactly one of brand (map onto an existing kit) and adopt (make a new kit from the file's own layouts). "
         "Then read import-report.md: unplaced content is in each slide's notes.", ("import",), (
             Arg("pptx", TEXT, path=ROOT, required=True, about="the .pptx to import; treated as untrusted"),
             Arg("out", TEXT, path=ROOT, required=True, about="the folder to write into, e.g. workspace/decks/refresh"),
             Arg("brand", SLUG, "--brand", about="map onto this existing brand"),
             Arg("adopt", SLUG, "--adopt", about="the slug for a new kit made from the file's own layouts"),
             FORCE)),
    Tool("brand_list", "List the brands: slug, name, version, path and whether each is valid.", ("brand", "list")),
    Tool("brand_show", "What a deck can use in a brand: its layouts with each field's kind and character budget "
         "(kind<=chars, xN bullets, * required), palette names, logo and icon ids, and which layouts show slide "
         "numbers and footers. Read it before writing a deck.", ("brand", "show"), (SLUG_ARG,)),
    Tool("brand_check", "Check a brand kit: schemas, the template mapping, assets and color contrast "
         "(LOW_CONTRAST is a warning for the user, not something to fix by hand).", ("brand", "check"),
         (SLUG_ARG,)),
    Tool("brand_init", "Generate a brand kit (template.potx and tokens.yaml) from a brand.yaml into a brand_paths "
         "folder. Asset paths in the brand.yaml are relative to its own folder.", ("brand", "init"), (
             SLUG_ARG,
             Arg("from", TEXT, "--from", BRAND_READ, required=True, about="the brand.yaml to generate from"),
             Arg("out", TEXT, "--out", BRAND_WRITE, about="a brand_paths folder (default: the first)"),
             FORCE)),
    Tool("brand_adopt", "Wrap an existing .potx or .pptx template as a brand kit, with starter tokens.yaml and "
         "brand.yaml to fill in.", ("brand", "adopt"), (
             SLUG_ARG,
             Arg("template", TEXT, "--template", BRAND_READ, required=True, about="the .potx or .pptx to wrap"),
             Arg("out", TEXT, "--out", BRAND_WRITE, about="a brand_paths folder (default: the first)"),
             FORCE)),
    Tool("brand_add_asset", "Copy a PNG into a brand kit as a logo or an icon. A new logo also needs a line under "
         "logos: in the kit's brand.yaml; the result says which.", ("brand", "add-asset"), (
             SLUG_ARG,
             Arg("file", TEXT, path=BRAND_READ, required=True, about="the PNG, inside the workspace"),
             Arg("as", {"type": "string", "pattern": "^(logo|icon)/[a-z0-9][a-z0-9-]*$"}, "--as", required=True,
                 about="logo/<id> or icon/<id>, e.g. logo/mono"),
             FORCE)),
    Tool("inspect", "A template's layouts, placeholders (idx, type, position, size) and theme.", ("inspect",), (
        Arg("template", TEXT, path=BRAND_READ, required=True, about="a .potx or .pptx"),
        Arg("yaml", FLAG, "--yaml", about="also a starter layouts block for tokens.yaml"))),
    Tool("assets", "Inventory a brand's assets (pass its slug) or a deck's (pass its path), with the slides that "
         "use each.", ("assets",), (
             Arg("target", TEXT, path=SLUG_OR_ROOT, required=True, about="a brand slug or a deck path"),)),
    Tool("docs", "A reference topic: deck-md, workbook, brand-yaml, tokens-yaml, workflow or codes. With no topic, "
         "the list.", ("docs",), (
             Arg("topic", {"type": "string", "pattern": "^[a-z][a-z-]*$"}, about="e.g. deck-md"),)),
    Tool("explain", "The cause and fix for one issue code.", ("explain",), (
        Arg("code", {"type": "string", "pattern": "^[A-Za-z_]+$"}, required=True, about="e.g. BUDGET_CHARS"),)),
    Tool("doctor", "What this machine can do: dependencies, render backends, the config and these tools.",
         ("doctor",)),
)}


class Refused(Exception):
    """A tool call this server won't run, with the reason the agent sees."""


class Server:
    def __init__(self, cfg: cfgmod.Config) -> None:
        assert cfg.path is not None
        self.cfg = cfg
        self.root = cfg.path.parent.resolve()  # relative paths resolve against this, as they always have
        self.workspace = cfg.workspace.resolve()
        self.brands = [p.resolve() for p in cfg.brand_paths]
        from deck_builder import cli  # the CLI's own parser and handlers

        self.cli = cli
        self.parser, self.handlers = cli.build_parser()

    # -- confinement

    def _off_limits(self, full: Path) -> bool:
        """This clone's own files: refused no matter what the workspace or brand_paths allow.

        Compared case-insensitively: on the default case-insensitive, case-preserving macOS volume,
        `full` can spell a name or folder in different case than written here (`claude.md`, `Src/`,
        `.Claude/`) and still name the same file or folder.
        """
        if full.name.casefold() in {"agents.md", "claude.md", "deck-builder.toml"}:
            return True
        parts = tuple(p.casefold() for p in full.parts)
        for d in (self.root / ".claude", self.root / ".git", self.root / "src"):
            dparts = tuple(p.casefold() for p in d.parts)
            if parts[: len(dparts)] == dparts:
                return True
        return False

    def _path(self, arg: Arg, value: str) -> str:
        if arg.path == SLUG_OR_ROOT and jsonschema.Draft202012Validator(SLUG).is_valid(value):
            return value  # a brand slug, not a path
        p = Path(value)
        try:
            full = (p if p.is_absolute() else self.root / p).resolve()  # follows symlinks
        except (ValueError, OSError) as e:  # a NUL byte, a symlink loop
            raise Refused(f"{arg.name}: {value!r} isn't a usable path ({e})") from None
        if self._off_limits(full):
            raise Refused(f"{arg.name}: {value!r} is part of this clone's own files, not the workspace")
        allowed = {ROOT: [self.workspace], SLUG_OR_ROOT: [self.workspace], BRAND_WRITE: self.brands,
                   BRAND_READ: [self.workspace, *self.brands]}[str(arg.path)]
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
        try:  # argparse prints help to stdout and errors to stderr; stdout belongs to the protocol
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(err):
                args = self.parser.parse_args(argv)
        except SystemExit:
            return _text(f"refused: {err.getvalue().strip().splitlines()[-1] if err.getvalue() else 'bad arguments'}",
                         error=True)
        try:
            # Checking an argument path doesn't confine what a command derives from it afterward (a
            # manifest beside a build output, a render folder beside a .pptx, a slug appended to a
            # brand path, ...); guard() catches those for the whole call, wherever the engine derives one.
            with contextlib.redirect_stdout(sys.stderr), confine.scoped(self.workspace, *self.brands):
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
                "instructions": (
                    f"deck-builder tools, confined to the workspace at {self.workspace} (brand tools also reach "
                    "the configured brand_paths folders); relative paths resolve against the folder holding "
                    "deck-builder.toml, but the result must land inside the workspace, and this clone's own "
                    ".claude, .git and src folders are refused regardless. The usual loop: brand_show and docs "
                    "deck-md once, write the deck file, check until it has no errors (explain gives each "
                    "code's fix), then check with render: true and read only the flagged slides' PNGs."),
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
