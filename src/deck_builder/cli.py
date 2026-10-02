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
from deck_builder.errors import EXIT_ENV, EnvError, Issue, Result

Handler = Callable[[argparse.Namespace], Result]


def _not_implemented(name: str) -> Handler:
    def run(args: argparse.Namespace) -> Result:
        r = Result(command=name, ok=False, exit_code=EXIT_ENV)
        r.issues.append(Issue("NOT_IMPLEMENTED", f"`{name}` isn't built in {__version__} yet"))
        return r

    return run


def build_parser() -> tuple[argparse.ArgumentParser, dict[str, Handler]]:
    ap = argparse.ArgumentParser(
        prog="deck-builder",
        description="Build branded, editable PowerPoint decks from markdown or spreadsheets.",
    )
    ap.add_argument("--version", action="version", version=f"deck-builder {__version__}")
    ap.add_argument("--config", help="config file (default: nearest deck-builder.toml)")
    sub = ap.add_subparsers(dest="command", metavar="<command>")
    handlers: dict[str, Handler] = {}

    def add(name: str, help_: str, handler: Handler | None = None) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_, description=help_)
        p.add_argument("--json", action="store_true", help="print one JSON object")
        handlers[name] = handler or _not_implemented(name)
        return p

    p = add("docs", "print a reference topic; no topic lists them", commands.docs_cmd)
    p.add_argument("topic", nargs="?")
    p = add("explain", "print the cause and fix for an issue code", commands.explain)
    p.add_argument("code")

    p = add("init", "create the workspace, config, neutral example brand and example decks", commands.init_cmd)
    p.add_argument("--dir", help="where to write deck-builder.toml (default: the current directory)")
    p = add("doctor", "check dependencies, render backends and permissions", commands.doctor_cmd)
    p.add_argument("--powerpoint", action="store_true",
                   help="also test PowerPoint automation (launches PowerPoint; the first run shows a macOS prompt)")
    p = add("brand", "list, show, check, init or adopt brand kits", commands.brand_cmd)
    p.add_argument("action", choices=["list", "show", "check", "init", "adopt"])
    p.add_argument("slug", nargs="?")
    p.add_argument("--from", dest="from_", metavar="BRAND_YAML", help="init: the brand.yaml to generate from")
    p.add_argument("--template", help="adopt: the .potx or .pptx to wrap")
    p.add_argument("--out", help="folder to create the kit in (default: the first brand_paths entry)")
    p.add_argument("--force", action="store_true", help="replace the generated files of an existing kit")
    p = add("inspect", "list a template's layouts and placeholders", commands.inspect_cmd)
    p.add_argument("template")
    p.add_argument("--yaml", action="store_true", help="print a starter layouts block for tokens.yaml")
    p = add("assets", "inventory a brand's or a deck's assets", commands.assets_cmd)
    p.add_argument("target")
    p = add("check", "validate a deck without building it", commands.check)
    p.add_argument("deck")
    p.add_argument("--brand", help="brand slug (overrides the deck's brand:)")
    p.add_argument("--render", action="store_true", help="also build, render and measure")
    p = add("build", "build a deck into a .pptx", commands.build)
    p.add_argument("deck")
    p.add_argument("--brand", help="brand slug (overrides the deck's brand:)")
    p.add_argument("-o", "--output")
    p.add_argument("--data", help="bulk mode: one deck per row of this csv or xlsx")
    p.add_argument("--name", help="bulk mode file name pattern, e.g. '{{client}}.pptx'")
    p = add("convert", "convert a deck between .md, .xlsx and .csv, losing nothing", commands.convert_cmd)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--force", action="store_true", help="replace the output file if it exists")
    p = add("render", "render a .pptx to PDF, slide PNGs and contact sheets; flags slides to look at",
            commands.render_cmd)
    p.add_argument("pptx")
    p.add_argument("--backend", choices=["auto", "powerpoint", "libreoffice"], default=None,
                   help="default from config: auto prefers PowerPoint, then LibreOffice")
    p.add_argument("--slides", help="only these slide numbers, comma-separated")
    p.add_argument("--dpi", type=int, help="PNG resolution (default from config, 96)")
    p = add("schema", "print a JSON Schema", commands.schema_cmd)
    p.add_argument("name", choices=["brand", "tokens", "manifest"])
    p = add("skills", "link this repo's skills and agent into another Claude Code setup")
    p.add_argument("action", choices=["install"])
    p.add_argument("--target")
    p.add_argument("--yes", action="store_true")
    return ap, handlers


def emit(result: Result, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.as_dict(), default=str))
        return
    for issue in result.issues:
        print(issue.human(), file=sys.stderr if issue.severity == "error" else sys.stdout)
    if result.summary:
        print(result.summary)


def main(argv: list[str] | None = None) -> int:
    ap, handlers = build_parser()
    args = ap.parse_args(argv)
    if not args.command:
        ap.print_help()
        return EXIT_ENV
    as_json = bool(getattr(args, "json", False))
    try:
        result = handlers[args.command](args)
    except EnvError as e:
        result = Result(command=args.command, ok=False, exit_code=EXIT_ENV)
        if as_json:
            result.data["error"] = str(e)
            if e.code:
                result.data["code"] = e.code
        else:
            print(f"error{' ' + e.code if e.code else ''}: {e}", file=sys.stderr)
    emit(result, as_json)
    return result.exit_code
