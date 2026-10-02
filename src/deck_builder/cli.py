"""The deck-builder command line. One surface for people and agents.

Human output is terse: one line per issue, then one summary line. `--json` prints one object.
Exit codes: 0 success, 1 validation issues, 2 usage or environment errors.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable

from deck_builder import __version__, commands
from deck_builder.errors import EXIT_ENV, EnvError, Result

Handler = Callable[[argparse.Namespace], Result]


def build_parser() -> tuple[argparse.ArgumentParser, dict[str, Handler]]:
    """Every subcommand and its handler. The MCP server parses tool calls with this same parser."""
    ap = argparse.ArgumentParser(
        prog="deck-builder",
        description="Build branded, editable PowerPoint decks from markdown or spreadsheets.",
    )
    ap.add_argument("--version", action="version", version=f"deck-builder {__version__}")
    ap.add_argument("--config", help="config file (default: nearest deck-builder.toml)")
    sub = ap.add_subparsers(dest="command", metavar="<command>")
    handlers: dict[str, Handler] = {}

    def add(name: str, help_: str, handler: Handler) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_, description=help_)
        p.add_argument("--json", action="store_true", help="print one JSON object")
        handlers[name] = handler
        return p

    p = add("docs", "print a reference topic; no topic lists them", commands.docs_cmd)
    p.add_argument("topic", nargs="?", help="deck-md, workbook, brand-yaml, tokens-yaml, workflow or codes")
    p = add("explain", "print the cause and fix for an issue code", commands.explain)
    p.add_argument("code", help="an issue code from a check or build, e.g. BUDGET_CHARS")

    p = add("init", "create the workspace, config, neutral example brand and example decks", commands.init_cmd)
    p.add_argument("--dir", help="where to write deck-builder.toml (default: the current directory)")
    p = add("doctor", "check dependencies, render backends and permissions", commands.doctor_cmd)
    p.add_argument("--powerpoint", action="store_true",
                   help="also test PowerPoint automation (launches PowerPoint; the first run shows a macOS prompt)")
    p = add("brand", "list, show, check, init or adopt brand kits, or add a logo or icon", commands.brand_cmd)
    p.add_argument("action", choices=["list", "show", "check", "init", "adopt", "add-asset"],
                   help="list brands; show one's layouts and budgets; check a kit; init a kit from brand.yaml; "
                        "adopt a template; add-asset to copy a logo or icon in")
    p.add_argument("slug", nargs="?", help="the brand's slug, e.g. neutral (every action but list)")
    p.add_argument("file", nargs="?", help="add-asset: the PNG to copy into the kit")
    p.add_argument("--as", dest="as_", metavar="KIND/ID", help="add-asset: logo/<id> or icon/<id>")
    p.add_argument("--from", dest="from_", metavar="BRAND_YAML", help="init: the brand.yaml to generate from")
    p.add_argument("--template", help="adopt: the .potx or .pptx to wrap")
    p.add_argument("--out", help="folder to create the kit in (default: the first brand_paths entry)")
    p.add_argument("--force", action="store_true",
                   help="replace the generated files of an existing kit, or an existing asset")
    p = add("inspect", "list a template's layouts and placeholders", commands.inspect_cmd)
    p.add_argument("template", help="a .potx or .pptx")
    p.add_argument("--yaml", action="store_true", help="print a starter layouts block for tokens.yaml")
    p = add("assets", "inventory a brand's or a deck's assets", commands.assets_cmd)
    p.add_argument("target", help="a brand slug, or a deck file to list the assets its slides use")
    deck_help = "a deck.md, deck.xlsx or deck.csv file, or the folder holding it"
    p = add("check", "validate a deck without building it", commands.check)
    p.add_argument("deck", help=deck_help)
    p.add_argument("--brand", help="brand slug (overrides the deck's brand:)")
    p.add_argument("--render", action="store_true", help="also build, render and measure")
    p.add_argument("--force", action="store_true",
                   help="with --render: replace the output even if it was hand-edited after a previous build")
    p = add("build", "build a deck into a .pptx", commands.build)
    p.add_argument("deck", help=deck_help)
    p.add_argument("--brand", help="brand slug (overrides the deck's brand:)")
    p.add_argument("-o", "--output", help="the .pptx to write, or a folder to write it in; with --data, a folder "
                                          "(default: <workspace>/out/)")
    p.add_argument("--data", help="bulk mode: one deck per row of this csv or xlsx")
    p.add_argument("--name", help="bulk mode file name pattern, e.g. '{{client}}.pptx'")
    p.add_argument("--force", action="store_true",
                   help="replace the output even if it was hand-edited after a previous build")
    p = add("convert", "convert a deck between .md, .xlsx and .csv, losing nothing", commands.convert_cmd)
    p.add_argument("input", help="the deck to convert: .md, .xlsx or .csv")
    p.add_argument("output", help="the file to write; its extension (.md, .xlsx or .csv) picks the format")
    p.add_argument("--force", action="store_true", help="replace the output file if it exists")
    p = add("import", "turn an existing .pptx back into deck.md, its images and a report of what needs a decision",
            commands.import_cmd)
    p.add_argument("pptx", help="the .pptx to import; it's treated as untrusted")
    p.add_argument("out", help="the folder to write deck.md, assets/ and import-report.md into")
    which = p.add_mutually_exclusive_group(required=True)
    which.add_argument("--brand", help="map the slides onto this existing brand kit (also how a deck is re-branded)")
    which.add_argument("--adopt", metavar="SLUG",
                       help="make a new kit from the file's own masters and layouts, then map onto it")
    p.add_argument("--force", action="store_true", help="replace an existing deck.md, or an adopted kit's files")
    p = add("render", "render a .pptx to PDF, slide PNGs and contact sheets; flags slides to look at",
            commands.render_cmd)
    p.add_argument("pptx", help="a built .pptx (to build and render a deck in one step: check --render)")
    p.add_argument("--backend", choices=["auto", "powerpoint", "libreoffice"], default=None,
                   help="default from config: auto prefers PowerPoint, then LibreOffice")
    p.add_argument("--slides", help="only these slide numbers, comma-separated")
    p.add_argument("--dpi", type=int, help="PNG resolution (default from config, 96)")
    sub.add_parser("mcp", help="serve the engine as MCP tools over stdio, confined to the workspace (for agents)",
                   description="serve the engine as MCP tools over stdio, confined to the workspace (for agents)")
    p = add("schema", "print a JSON Schema", commands.schema_cmd)
    p.add_argument("name", choices=["brand", "tokens", "manifest"],
                   help="brand.yaml, tokens.yaml, or a build's manifest.json")
    p = add("skills", "link this clone's skills and agent into another Claude Code setup", commands.skills_cmd)
    p.add_argument("action", choices=["install"], help="install: link the skills and agents (needs --yes)")
    p.add_argument("--target", help="the Claude Code folder to link into (default: ~/.claude)")
    p.add_argument("--yes", action="store_true", help="create the links; without it, only show the plan")
    return ap, handlers


def emit(result: Result, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.as_dict(), default=str))
        return
    for issue in result.issues:
        print(issue.human(), file=sys.stderr if issue.severity == "error" else sys.stdout)
    codes = sorted({i.code for i in result.issues if i.severity == "error"})
    if codes:
        also = f" (also {', '.join(codes[1:])})" if codes[1:] else ""
        print(f"for the fix: deck-builder explain {codes[0]}{also}", file=sys.stderr)
    if result.summary:
        print(result.summary)


def run(handler: Handler, args: argparse.Namespace) -> Result:
    """Run one command; an environment problem becomes a Result with `error` (and `code`) and exit 2."""
    try:
        return handler(args)
    except EnvError as e:
        result = Result(command=args.command, ok=False, exit_code=EXIT_ENV)
        result.data["error"] = str(e)
        if e.code:
            result.data["code"] = e.code
        return result


def main(argv: list[str] | None = None) -> int:
    ap, handlers = build_parser()
    args = ap.parse_args(argv)
    if not args.command:
        ap.print_help()
        return EXIT_ENV
    if args.command == "mcp":
        from deck_builder import mcp

        return mcp.serve(args.config)
    as_json = bool(getattr(args, "json", False))
    result = run(handlers[args.command], args)
    if "error" in result.data and not as_json:
        code = result.data.get("code")
        print(f"error{' ' + code if code else ''}: {result.data['error']}", file=sys.stderr)
    emit(result, as_json)
    return result.exit_code
