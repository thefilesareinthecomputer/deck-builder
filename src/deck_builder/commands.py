"""Command handlers. Each takes parsed args and returns a Result; cli.py prints it."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml

from deck_builder import config as cfgmod
from deck_builder import docs, pipeline, validate
from deck_builder.brand import inspect as brand_inspect
from deck_builder.brand import kit, registry, schema
from deck_builder.brand.registry import Brand
from deck_builder.build.deck import build as build_deck
from deck_builder.build.deck import manifest_path
from deck_builder.errors import CODES, EnvError, Issue, Result
from deck_builder.model import Deck
from deck_builder.parse.csvfile import read_rows as read_csv_rows
from deck_builder.parse.markdown import TOKEN

SAFE = re.compile(r"[^\w.-]+")


def read_data_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise EnvError(f"data file not found: {path}")
    if path.suffix.lower() == ".csv":
        return read_csv_rows(path)
    if path.suffix.lower() == ".xlsx":
        from deck_builder.parse.workbook import read_table_rows

        return read_table_rows(path)
    raise EnvError(f"--data takes .csv or .xlsx, not {path.suffix!r}")


def _cfg(args: argparse.Namespace) -> cfgmod.Config:
    return cfgmod.load(getattr(args, "config", None))


def _tally(r: Result) -> str:
    errs = sum(1 for i in r.issues if i.severity == "error")
    warns = len(r.issues) - errs
    return f"{errs} error{'s' * (errs != 1)}, {warns} warning{'s' * (warns != 1)}"


def docs_cmd(args: argparse.Namespace) -> Result:
    r = Result(command="docs")
    if not args.topic:
        r.data["topics"] = docs.topics()
        r.summary = "\n".join(f"{k:<12} {v}" for k, v in docs.topics().items())
        return r
    text = docs.read(args.topic)
    r.data["topic"] = args.topic
    r.data["text"] = text
    r.summary = text.rstrip("\n")
    return r


def explain(args: argparse.Namespace) -> Result:
    code = args.code.upper()
    if code not in CODES:
        raise EnvError(f"unknown issue code {args.code!r}; `deck-builder docs codes` lists them")
    cause, fix = CODES[code]
    r = Result(command="explain", data={"code": code, "cause": cause, "fix": fix})
    r.summary = f"{code}\ncause: {cause}\nfix:   {fix}"
    return r


def _validated(path: Path, cfg: cfgmod.Config, r: Result, brand_slug: str | None,
               row: dict[str, str] | None = None) -> tuple[Deck | None, Brand | None]:
    """Parse and validate into r. Returns the resolved deck and brand, or (None, brand) if any error."""
    loaded = pipeline.load_deck(path, row)
    for i in loaded.issues:
        r.add(i)
    r.data["slides"] = len(loaded.deck.slides)
    if any(i.code == "UNKNOWN_TOKEN" for i in loaded.issues):
        return None, None
    brand = pipeline.brand_for(loaded.deck, path, cfg, brand_slug)
    r.data["brand"] = brand.slug
    for p in brand.problems:
        r.add(Issue("BRAND_INVALID", f"brand {brand.slug!r}: {p}"))
    for e in brand.schema_errors:
        r.add(Issue("SCHEMA", f"brand {brand.slug!r}: {e}"))
    if not brand.valid:
        return None, brand
    resolved, issues = validate.resolve(loaded.deck, brand, path.parent)
    for i in issues:
        r.add(i)
    return (resolved if r.ok else None), brand


def schema_cmd(args: argparse.Namespace) -> Result:
    data = schema.load(args.name)
    r = Result(command="schema", data={"schema": data})
    r.summary = json.dumps(data, indent=2)
    return r


def brand_cmd(args: argparse.Namespace) -> Result:
    cfg = _cfg(args)
    r = Result(command=f"brand {args.action}")
    if args.action == "list":
        brands, issues = registry.discover(cfg)
        for i in issues:
            r.add(i)
        rows = [{"slug": b.slug, "name": b.name, "version": b.version, "path": str(b.path), "valid": b.valid}
                for b in brands.values()]
        r.data["brands"] = rows
        if not cfg.found:
            r.data["config"] = None
            r.summary = "no deck-builder.toml found; run `deck-builder init` (or the deck-onboard skill)"
        else:
            lines = [f"{x['slug']:<16} {x['version']:<8} {'ok' if x['valid'] else 'INVALID':<8} {x['path']}"
                     for x in rows]
            r.summary = "\n".join(lines) or f"no brands under {', '.join(map(str, cfg.brand_paths))}"
        return r
    if args.action in ("show", "check"):
        if not args.slug:
            raise EnvError(f"brand {args.action} needs a slug; `deck-builder brand list` shows them")
        b = registry.get(cfg, args.slug)
        if args.action == "show":
            if not b.valid:
                for i in kit.check_kit(b):
                    r.add(i)
                r.summary = f"brand {b.slug!r} is invalid; run `deck-builder brand check {b.slug}`"
                return r
            d = kit.show(b)
            r.data.update(d)
            r.summary = kit.show_text(d)
            return r
        for i in kit.check_kit(b):
            r.add(i)
        r.data["slug"] = b.slug
        r.summary = f"{'ok' if r.ok else 'failed'} brand check {b.slug}: {_tally(r)}"
        return r
    if args.action == "adopt":
        return _adopt(args, cfg, r)
    r.ok = False
    r.exit_code = 2
    r.issues.append(Issue("NOT_IMPLEMENTED", f"`brand {args.action}` isn't built yet"))
    return r


def _kit_dir(args: argparse.Namespace, cfg: cfgmod.Config) -> Path:
    if not args.slug or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.slug):
        raise EnvError("a brand slug is lowercase letters, digits and hyphens, e.g. `acme` or `acme-2026`")
    root = Path(args.out) if args.out else cfg.brand_paths[0]
    target = root / args.slug
    if (target / "brand.yaml").exists() and not args.force:
        raise EnvError(f"{target} already holds a brand kit; pass --force to replace its generated files")
    return target


def _write_yaml(path: Path, data: dict[str, Any], header: str) -> None:
    path.write_text(header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=110), encoding="utf-8")


def _adopt(args: argparse.Namespace, cfg: cfgmod.Config, r: Result) -> Result:
    if not args.template:
        raise EnvError("brand adopt needs --template FILE (.potx or .pptx)")
    src = Path(args.template)
    if not src.is_file() or src.suffix.lower() not in (".potx", ".pptx"):
        raise EnvError(f"not a .potx or .pptx file: {src}")
    target = _kit_dir(args, cfg)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, target / f"template{src.suffix.lower()}")
    _write_yaml(target / "tokens.yaml", brand_inspect.starter_tokens(src),
                "# Generated by `deck-builder brand adopt`. Rename layout keys and fields to suit;\n"
                "# max_chars values are estimates - tune them after a test render.\n")
    _write_yaml(target / "brand.yaml", brand_inspect.brand_skeleton(args.slug, src),
                "# Generated by `deck-builder brand adopt` from the template's theme. Rename palette entries\n"
                "# by role, and add logos, icons, voice and lint rules (`deck-builder docs brand-yaml`).\n")
    b = registry.load_kit(target)
    for i in kit.check_kit(b):
        r.add(i)
    r.data.update({"slug": args.slug, "path": str(target), "layouts": b.layout_names()})
    r.summary = (f"{'ok' if r.ok else 'failed'} brand adopt {args.slug}: {len(b.layout_names())} layouts "
                 f"at {target}, {_tally(r)}")
    return r


def inspect_cmd(args: argparse.Namespace) -> Result:
    path = Path(args.template)
    if not path.is_file():
        raise EnvError(f"template not found: {path}")
    r = Result(command="inspect")
    if args.yaml:
        starter = brand_inspect.starter_tokens(path)
        r.data["tokens"] = starter
        r.summary = yaml.safe_dump(starter, sort_keys=False, width=110).rstrip()
        return r
    report = brand_inspect.layouts_report(path)
    r.data["layouts"] = report
    r.data["theme"] = brand_inspect.theme(path)
    lines = []
    for lay in report:
        lines.append(f"[master {lay['master']} / layout {lay['index']}] {lay['name']!r}")
        for ph in lay["placeholders"]:
            lines.append(f"  idx={ph['idx']:<3} {ph['type']:<14} at={ph['at_in']} size={ph['size_in']}in "
                         f"{ph['name']!r}")
    r.summary = "\n".join(lines)
    return r


def check(args: argparse.Namespace) -> Result:
    cfg = _cfg(args)
    path = Path(args.deck)
    r = Result(command="check", data={"input": str(path)})
    _validated(path, cfg, r, args.brand)
    r.summary = f"{'ok' if r.ok else 'failed'} check {path.name}: {r.data['slides']} slides, {_tally(r)}"
    return r


def default_output(path: Path, deck: Deck | None, cfg: cfgmod.Config) -> Path:
    """-o wins (handled by the caller); then front matter `output`; then <workspace>/out/<name>.pptx.

    A file named deck.md or deck.xlsx takes its folder's name, so decks/q3/deck.md builds out/q3.pptx.
    """
    if deck is not None and deck.meta.get("output"):
        return path.parent / str(deck.meta["output"])
    name = path.parent.name if path.stem == "deck" else path.stem
    out_dir = cfg.workspace / "out" if cfg.found else path.parent
    return out_dir / f"{name}.pptx"


def _cache_dir(cfg: cfgmod.Config) -> Path:
    return cfg.workspace / ".cache" / "assets" if cfg.found else Path(tempfile.gettempdir()) / "deck-builder-cache"


def _build_one(path: Path, cfg: cfgmod.Config, args: argparse.Namespace, out: Path | None,
               row: dict[str, str] | None, r: Result) -> dict[str, Any] | None:
    deck, brand = _validated(path, cfg, r, args.brand, row)
    if deck is None or brand is None:
        return None
    out_path = out or default_output(path, deck, cfg)
    manifest, issues = build_deck(deck, brand, path, out_path, _cache_dir(cfg))
    for i in issues:
        r.add(i)
    return {"output": str(out_path), "manifest": str(manifest_path(out_path)), "slides": len(manifest["slides"])}


def build(args: argparse.Namespace) -> Result:
    cfg = _cfg(args)
    path = Path(args.deck)
    r = Result(command="build", data={"input": str(path)})
    if not args.data:
        done = _build_one(path, cfg, args, Path(args.output) if args.output else None, None, r)
        if done:
            r.data.update(done)
            r.summary = f"{'ok' if r.ok else 'failed'} build {done['output']}: {done['slides']} slides, {_tally(r)}"
        else:
            r.summary = f"failed build {path.name}: {_tally(r)}"
        return r

    rows = read_data_rows(Path(args.data))
    pattern = args.name or "{{_row}}.pptx"
    out_dir = Path(args.output) if args.output else default_output(path, None, cfg).with_suffix("")
    built = []
    for n, row in enumerate(rows, start=1):
        row = {**row, "_row": f"{n:03d}"}
        name = TOKEN.sub(lambda m, row=row: SAFE.sub("-", str(row.get(m.group(1), m.group(0)))), pattern)
        sub = Result(command="build")
        done = _build_one(path, cfg, args, out_dir / name, row, sub)
        for i in sub.issues:
            i.message = f"row {n}: {i.message}"
            r.add(i)
        if done:
            built.append(done)
    r.data["outputs"] = built
    r.summary = f"{'ok' if r.ok else 'failed'} build {len(built)} of {len(rows)} decks into {out_dir}, {_tally(r)}"
    return r
