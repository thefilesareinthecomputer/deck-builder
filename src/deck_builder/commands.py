"""Command handlers. Each takes parsed args and returns a Result; cli.py prints it."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import tempfile
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from PIL import Image as PILImage

from deck_builder import __version__, confine, docs, doctor, importer, pipeline, skills, validate
from deck_builder import assets as asset_inventory
from deck_builder import config as cfgmod
from deck_builder import template as tpl
from deck_builder.brand import generate, kit, registry, schema
from deck_builder.brand import inspect as brand_inspect
from deck_builder.brand.registry import Brand
from deck_builder.build.deck import build as build_deck
from deck_builder.build.deck import furniture_settings, manifest_path
from deck_builder.errors import CODES, EnvError, Issue, Result
from deck_builder.model import Deck
from deck_builder.parse import markdown as markdown_parser
from deck_builder.parse.csvfile import read_rows as read_csv_rows
from deck_builder.parse.markdown import TOKEN
from deck_builder.qa import backends as qa_backends
from deck_builder.qa import render as qa_render
from deck_builder.write import csvfile as csv_writer
from deck_builder.write import markdown as md_writer
from deck_builder.write import workbook as wb_writer

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


def _bulk_name(pattern: str, row: dict[str, str]) -> tuple[str, list[str]]:
    """A bulk output name for one row, and any {{token}} in pattern that row has no column for."""
    unresolved: list[str] = []

    def rep(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in row:
            unresolved.append(key)
            return SAFE.sub("-", m.group(0))
        return SAFE.sub("-", str(row[key]))

    return TOKEN.sub(rep, pattern), unresolved


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
    if any(i.code in ("UNKNOWN_TOKEN", "BAD_DATA_VALUE") for i in loaded.issues):
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
    r.data["content_sha256"] = pipeline.content_sha(loaded.deck)
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
    if args.action == "add-asset":
        return _add_asset(args, cfg, r)
    return _init_brand(args, cfg, r)


def _add_asset(args: argparse.Namespace, cfg: cfgmod.Config, r: Result) -> Result:
    """Copy a PNG into a kit as a logo or an icon, so placing an asset needs no shell."""
    m = re.fullmatch(r"(logo|icon)/([a-z0-9][a-z0-9-]*)", args.as_ or "")
    if not args.slug or not args.file or not m:
        raise EnvError("brand add-asset needs a slug, a PNG file and --as logo/<id> or icon/<id> "
                       "(an id is lowercase letters, digits and hyphens)")
    src = Path(args.file)
    if not src.is_file():
        raise EnvError(f"not found: {src}")
    try:
        with PILImage.open(src) as im:
            is_png = im.format == "PNG"
    except (OSError, ValueError):
        is_png = False
    if not is_png:
        raise EnvError(f"{src.name} isn't a PNG; convert it first")
    b = registry.get(cfg, args.slug)
    kind, aid = m.groups()
    logos = b.meta.get("logos") or {}
    if kind == "icon":
        icons_dir = (b.meta.get("icons") or {}).get("dir")
        if not icons_dir:
            raise EnvError(f"brand {b.slug!r} has no icons: dir in brand.yaml; add one first")
        rel = f"{icons_dir}/{aid}.png"
    else:
        rel = str(logos.get(aid) or f"assets/{aid}.png")
    dest = inside(b.path, rel)
    if dest.exists() and not args.force:
        raise EnvError(f"{rel} already exists in brand {b.slug!r}; pass --force to replace it")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    r.data.update({"slug": b.slug, "path": str(dest), "ref": f"brand:{kind}/{aid}"})
    todo = "" if kind == "icon" or aid in logos else f"; add `{aid}: {rel}` under logos: in brand.yaml to use it"
    r.summary = f"ok brand add-asset {b.slug}: brand:{kind}/{aid} at {rel}{todo}"
    return r


DEFAULT_CONFIG = """\
# deck-builder config, written by `deck-builder init`. Paths are relative to this file.
workspace = "workspace"
brand_paths = ["workspace/brands"]
default_brand = "neutral"

[render]
backend = "auto"     # auto prefers LibreOffice, then PowerPoint
dpi = 96
contact_batch = 20   # slides per contact sheet
"""


def init_cmd(args: argparse.Namespace) -> Result:
    """Create what's missing; never change what exists. A second run reports nothing to do."""
    root = Path(args.dir).resolve() if args.dir else Path.cwd()
    cfg_path = root / cfgmod.FILENAME
    created: list[str] = []
    if root.exists() and not root.is_dir():
        raise EnvError(f"{root} is a file; init needs a folder")
    if not root.exists():
        root.mkdir(parents=True)
        created.append(str(root))
    if not cfg_path.exists():
        cfg_path.write_text(DEFAULT_CONFIG, encoding="utf-8")
        created.append(str(cfg_path))
    cfg = cfgmod.load(str(cfg_path))
    for d in (cfg.brand_paths[0], cfg.workspace / "decks", cfg.workspace / "out", cfg.workspace / ".cache"):
        if not d.is_dir():
            d.mkdir(parents=True)
            created.append(str(d))
    data = resources.files("deck_builder") / "data"
    neutral = cfg.brand_paths[0] / "neutral"
    if not (neutral / "brand.yaml").exists():
        with resources.as_file(data / "brands" / "neutral") as src_dir:
            src = Path(src_dir) / "brand.yaml"
            init_kit(yaml.safe_load(src.read_text(encoding="utf-8")), src, neutral)
        created.append(str(neutral))
    with resources.as_file(data / "decks") as decks_dir:
        for example in sorted(Path(decks_dir).iterdir()):
            target = cfg.workspace / "decks" / example.name
            if example.is_dir() and not target.exists():
                shutil.copytree(example, target)
                (target / "source").mkdir(exist_ok=True)
                created.append(str(target))
    r = Result(command="init", data={"config": str(cfg_path), "workspace": str(cfg.workspace), "created": created})
    r.summary = (f"initialized {root}: created {len(created)} item(s); next: deck-builder brand list"
                 if created else f"{root} is already initialized; nothing changed")
    return r


def _init_brand(args: argparse.Namespace, cfg: cfgmod.Config, r: Result) -> Result:
    """Generate a kit from a brand.yaml. Without --from, regenerate an existing kit from its own brand.yaml
    and assets (its recipe and ingredients), which needs --force."""
    if args.from_:
        src = Path(args.from_)
    else:
        root = Path(args.out) if args.out else cfg.brand_paths[0]
        src = root / (args.slug or "") / "brand.yaml"
        if not src.is_file():
            raise EnvError("brand init needs --from brand.yaml for a new kit; to regenerate a kit from its own "
                           "brand.yaml, give the slug of an existing kit and --force")
    if not src.is_file():
        raise EnvError(f"brand.yaml not found: {src}")
    meta = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    errs = schema.errors("brand", meta)
    if errs:
        for e in errs:
            r.add(Issue("SCHEMA", e, file=src.name))
        r.summary = f"failed brand init: {_tally(r)}"
        return r
    if meta.get("slug") != args.slug:
        raise EnvError(f"{src.name} has slug {meta.get('slug')!r}; run `brand init {meta.get('slug')}` "
                       "or change the slug in the file")
    target = _kit_dir(args, cfg)
    r.data.update({"slug": args.slug, "path": str(target)})
    init_kit(meta, src, target)
    b = registry.load_kit(target)
    for i in kit.check_kit(b):
        r.add(i)
    r.data["layouts"] = b.layout_names()
    r.summary = (f"{'ok' if r.ok else 'failed'} brand init {args.slug}: {len(b.layout_names())} layouts at "
                 f"{target}, {_tally(r)}")
    return r


def inside(base: Path, rel: str) -> Path:
    """base/rel, refusing anything that would land outside base (absolute paths, `..`, symlinks out)."""
    p = Path(rel)
    full = (base / p).resolve()
    if p.is_absolute() or ".." in p.parts or not full.is_relative_to(base.resolve()):
        raise EnvError(f"{rel!r} must be a relative path inside {base}")
    return full


def init_kit(meta: dict[str, Any], src: Path, target: Path) -> None:
    """Write a generated kit: brand.yaml and its assets copied in, template.potx and tokens.yaml generated.

    Asset paths in brand.yaml are confined to the source folder and the kit, so a brand.yaml from
    elsewhere can't read or overwrite files outside them.
    """
    target.mkdir(parents=True, exist_ok=True)
    src_dir = src.parent.resolve()
    rels = [str(p) for p in (meta.get("logos") or {}).values()]
    icons_dir = (meta.get("icons") or {}).get("dir")
    if icons_dir and inside(src_dir, icons_dir).is_dir():
        rels += [str(Path(icons_dir) / p.name) for p in sorted(inside(src_dir, icons_dir).glob("*.png"))]
    pairs = [(inside(src_dir, rel), inside(target, rel)) for rel in rels]  # validate all before writing
    if src.resolve() != (target / "brand.yaml").resolve():
        shutil.copyfile(src, target / "brand.yaml")
        for source, dest in pairs:
            if source.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
    potx, tokens = generate.generate(meta, src_dir)
    (target / "template.potx").write_bytes(potx)
    stale = target / "template.pptx"
    if stale.exists():
        stale.unlink()
    # what made this kit, so `brand check` can say when the kit no longer matches its recipe and ingredients
    tokens = {"spec_version": tokens.pop("spec_version", 1),
              "generated": {"by": f"deck-builder {__version__}", "inputs_sha256": kit.inputs_sha(target, meta)},
              **tokens}
    _write_yaml(target / "tokens.yaml", tokens,
                "# Generated by `deck-builder brand init`. max_chars and bullet budgets are estimates;\n"
                "# tune them after a test render (`deck-builder docs tokens-yaml`).\n")


def _kit_dir(args: argparse.Namespace, cfg: cfgmod.Config) -> Path:
    if not args.slug or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.slug):
        raise EnvError("a brand slug is lowercase letters, digits and hyphens, e.g. `acme` or `acme-2026`")
    root = Path(args.out) if args.out else cfg.brand_paths[0]
    # the slug is appended after root was checked; that folder name can already be an existing
    # symlink pointing outside every allowed root (a no-op outside an MCP call).
    target = confine.guard(root / args.slug, "the kit folder")
    if (target / "brand.yaml").exists() and not args.force:
        replaced = "template, tokens.yaml and brand.yaml" if args.action == "adopt" else "template.potx and tokens.yaml"
        raise EnvError(f"{target} already holds a brand kit; --force replaces its {replaced}, discarding tuned "
                       "budgets and edits")
    return target


def _write_yaml(path: Path, data: dict[str, Any], header: str) -> None:
    path.write_text(header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=110), encoding="utf-8")


def _adopt(args: argparse.Namespace, cfg: cfgmod.Config, r: Result) -> Result:
    """Wrap a template as a kit. A .pptx is a deck, so its slides, their notes and their media are
    stripped before it becomes the kit's template; a .potx holds no slides, so it's copied as is."""
    if not args.template:
        raise EnvError("brand adopt needs --template FILE (.potx or .pptx)")
    src = Path(args.template)
    if not src.is_file() or src.suffix.lower() not in (".potx", ".pptx"):
        raise EnvError(f"not a .potx or .pptx file: {src}")
    target = _kit_dir(args, cfg)
    target.mkdir(parents=True, exist_ok=True)
    written = f"template{src.suffix.lower()}"
    slides_removed = 0
    sanitized: list[str] = []
    if src.suffix.lower() == ".pptx":
        prs = tpl.open_template(src)
        slides_removed = len(prs.slides)
        tpl.remove_all_slides(prs)  # slides, their notes and their media stop being saved
        sanitized = tpl.sanitize(prs)
        prs.save(str(target / written))
    else:
        shutil.copyfile(src, target / written)
    stale = target / next(n for n in registry.TEMPLATE_NAMES if n != written)
    if stale.is_file():  # a kit this replaces may have had the other extension; leave exactly one template
        stale.unlink()
    _write_yaml(target / "tokens.yaml", brand_inspect.starter_tokens(src),
                "# Generated by `deck-builder brand adopt`. Rename layout keys and fields to suit;\n"
                "# max_chars values are estimates - tune them after a test render.\n")
    _write_yaml(target / "brand.yaml", brand_inspect.brand_skeleton(args.slug, src),
                "# Generated by `deck-builder brand adopt` from the template's theme. Rename palette entries\n"
                "# by role, and add logos, icons, voice and lint rules (`deck-builder docs brand-yaml`).\n")
    b = registry.load_kit(target)
    for i in kit.check_kit(b):
        r.add(i)
    r.data.update({"slug": args.slug, "path": str(target), "layouts": b.layout_names(),
                   "slides_removed": slides_removed, "sanitized": sanitized})
    removed = f", {slides_removed} slide(s) removed" if slides_removed else ""
    cleaned = f", {len(sanitized)} external/embedded item(s) removed" if sanitized else ""
    r.summary = (f"{'ok' if r.ok else 'failed'} brand adopt {args.slug}: {len(b.layout_names())} layouts "
                 f"at {target}{removed}{cleaned}, {_tally(r)}")
    return r


def _first_difference(a: Deck, b: Deck) -> str:
    if a.meta != b.meta:
        return "front matter differs"
    if len(a.slides) != len(b.slides):
        return f"{len(a.slides)} slides became {len(b.slides)}"
    for n, (x, y) in enumerate(zip(a.slides, b.slides, strict=True), start=1):
        if x != y:
            keys = sorted(k for k in set(x.fields) | set(y.fields) if x.fields.get(k) != y.fields.get(k))
            what = f"fields {', '.join(keys)}" if keys else "title, layout or notes"
            return f"slide {n}: {what} would change"
    return "content differs"


def convert_cmd(args: argparse.Namespace) -> Result:
    """deck.md <-> deck.xlsx <-> .csv; the output is parsed back and refused with CONVERT_LOSSY if it differs."""
    cfg = _cfg(args)
    src, dst = Path(args.input), Path(args.output)
    fmt = pipeline.FORMATS.get(dst.suffix.lower())
    if fmt is None:
        raise EnvError(f"can't write {dst.suffix!r}; convert writes .md, .xlsx or .csv")
    if dst.exists() and not args.force:
        raise EnvError(f"{dst} exists; pass --force to replace it")
    r = Result(command="convert", data={"input": str(src), "output": str(dst)})
    loaded = pipeline.load_deck(src)
    for i in loaded.issues:
        r.add(i)
    if not r.ok:
        r.summary = f"failed convert {src.name}: fix the parse errors first, {_tally(r)}"
        return r
    deck = loaded.deck
    if fmt == "csv":
        for reason in csv_writer.lossy_reasons(deck):
            r.add(Issue("CONVERT_LOSSY", reason, file=src.name))
        if not r.ok:
            r.summary = f"failed convert {src.name} -> {dst.name}: CSV would lose content; use .xlsx, {_tally(r)}"
            return r
    brand = None
    with contextlib.suppress(EnvError):  # without a brand, a workbook has no layout dropdown or char counts
        brand = pipeline.brand_for(deck, src, cfg)
    if fmt == "markdown":
        blob = md_writer.write(deck).encode("utf-8")
    elif fmt == "workbook":
        blob = wb_writer.write(deck, brand if brand is not None and brand.valid else None)
    else:
        blob = csv_writer.write(deck).encode("utf-8")
    # Prove the conversion lost nothing before writing it: parse the output back and compare.
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / f"probe{dst.suffix.lower()}"
        probe.write_bytes(blob)
        back = pipeline.load_deck(probe)
    if back.issues or back.deck != deck:
        reason = "; ".join(i.message for i in back.issues) or _first_difference(deck, back.deck)
        r.add(Issue("CONVERT_LOSSY", reason, file=src.name))
        r.summary = f"failed convert {src.name} -> {dst.name}: {reason}"
        return r
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(blob)
    r.data["slides"] = len(deck.slides)
    r.summary = f"ok convert {src.name} -> {dst}: {len(deck.slides)} slides"
    return r


def _render_into(r: Result, pptx: Path, cfg: cfgmod.Config, backend_req: str | None, pages: list[int] | None,
                 dpi: int | None = None) -> None:
    mpath = manifest_path(pptx)
    brand = None
    if mpath.is_file():
        try:
            slug = json.loads(mpath.read_text())["brand"]["slug"]
        except (OSError, ValueError, KeyError, TypeError):
            slug = None  # not a manifest this engine wrote; render without brand-specific font checks
        if slug is not None:
            with contextlib.suppress(EnvError):
                brand = registry.get(cfg, slug)
    backend = qa_backends.choose(backend_req or cfg.render.backend)
    out = qa_render.render(pptx, backend, dpi or cfg.render.dpi, cfg.render.contact_batch, pages, brand)
    for i in out.issues:
        r.add(i)
    r.data.update({
        "backend": out.backend,
        "render_dir": str(out.out_dir),
        "pdf": str(out.pdf),
        "slide_png": str(out.out_dir / "slide-NN.png"),
        "flagged_slides": [{"slide": n, "codes": c} for n, c in out.flagged.items()],
        "contact_sheets": [str(p) for p in out.contact_sheets],
        "hidden_slides": out.hidden,
    })


def _pages(spec: str | None) -> list[int] | None:
    if not spec:
        return None
    try:
        return sorted({int(x) for x in spec.split(",") if x.strip()})
    except ValueError as e:
        raise EnvError("--slides takes slide numbers separated by commas, e.g. 3,7") from e


def skills_cmd(args: argparse.Namespace) -> Result:
    clone = skills.find_clone(Path.cwd())
    if doctor.mcp_command() is None:  # the agents reach the engine only through `deck-builder mcp`
        raise EnvError(f"deck-builder isn't on PATH, and the agents need it for their tools; install it first: "
                       f"uv tool install --editable {clone}")
    target = Path(args.target).expanduser() if args.target else Path("~/.claude").expanduser()
    links = skills.plan(clone, target)
    if args.yes:
        skills.apply(links)
    r = Result(command="skills install", data={
        "clone": str(clone), "target": str(target), "applied": bool(args.yes),
        "links": [{"source": str(x.source), "target": str(x.target), "status": x.status} for x in links]})
    for x in links:
        if x.status == "conflict":
            r.add(Issue("SKILL_CONFLICT", f"{x.target} exists and isn't a link to this clone; left as is",
                        severity="warning"))
    lines = [f"{x.status:<9} {x.target} -> {x.source}" for x in links]
    if not args.yes and any(x.status == "create" for x in links):
        lines.append("nothing changed; rerun with --yes to create these links")
    r.summary = "\n".join(lines)
    return r


def doctor_cmd(args: argparse.Namespace) -> Result:
    cfg = _cfg(args)
    checks = doctor.run(cfg, args.powerpoint)
    backend = doctor.render_backend(checks)
    mcp_check = next((c for c in checks if c.name == "agent tools (mcp)"), None)
    # Prefer what the spawned `deck-builder mcp` process reports about itself - that's the install
    # actually serving the agents' tools, which this doctor process need not match. Fall back to this
    # process's own distribution only when the probe couldn't tell (deck-builder missing, no config).
    editable = mcp_check.editable if mcp_check is not None and mcp_check.editable is not None \
        else doctor.editable_install()
    r = Result(command="doctor", data={"checks": [c.as_dict() for c in checks], "render_backend": backend,
                                       "can_build": all(c.status == "ok" for c in checks[:7]),
                                       "editable_install": editable})
    if not r.data["can_build"]:
        r.ok, r.exit_code = False, 2
    lines = [f"{c.status:<10} {c.name:<22} {c.detail}" + (f"\n{'':<10} fix: {c.fix}" if c.fix else "")
             for c in checks]
    if editable:
        lines.append(f"{'warning':<10} {'editable install':<22} agents' MCP server runs this clone's src/ live; "
                     "keep client workspaces outside the clone")
    lines.append(f"build: {'ready' if r.data['can_build'] else 'not ready'}; "
                 f"render: {backend or 'not available (install poppler and LibreOffice)'}")
    r.summary = "\n".join(lines)
    return r


def import_cmd(args: argparse.Namespace) -> Result:
    """An existing .pptx -> <out>/deck.md, <out>/assets/ and <out>/import-report.md."""
    cfg = _cfg(args)
    src = Path(args.pptx)
    if src.suffix.lower() != ".pptx" or not src.is_file():
        raise EnvError(f"import takes an existing .pptx file, not {src}")
    out = Path(args.out)
    if (out / "deck.md").exists() and not args.force:
        raise EnvError(f"{out / 'deck.md'} exists; pass --force to replace it")
    r = Result(command="import", data={"input": str(src)})
    if args.adopt:
        kit_dir = cfg.brand_paths[0] / args.adopt
        if (kit_dir / "brand.yaml").is_file():
            raise EnvError(f"brand {args.adopt!r} already exists at {kit_dir}; import onto it with "
                           f"--brand {args.adopt} instead of --adopt, or adopt under a different slug")
        # --force governs deck.md only (checked above); a freshly adopted kit is never regenerated here.
        ns = argparse.Namespace(slug=args.adopt, template=str(src), out=None, force=False, action="adopt")
        _adopt(ns, cfg, r)
        brand = registry.load_kit(Path(r.data["path"]))
    else:
        brand = registry.get(cfg, args.brand)
    if not brand.valid:
        raise EnvError(f"brand {brand.slug!r} is invalid; run `deck-builder brand check {brand.slug}`")
    imp = importer.import_pptx(src, brand, _cache_dir(cfg))
    confine.guard(out, "the import output folder")
    out.mkdir(parents=True, exist_ok=True)
    report = out / "import-report.md"
    colliding = [p for p in ([report] if report.is_file() else [])
                + [out / "assets" / name for name in imp.assets if (out / "assets" / name).is_file()]]
    if colliding and not args.force:
        raise EnvError(f"{', '.join(str(p) for p in colliding)} exist; pass --force to replace them")
    if imp.assets:
        assets_dir = confine.guard(out / "assets", "the import assets folder")
        assets_dir.mkdir(exist_ok=True)
        for name, blob in imp.assets.items():
            confine.guard(assets_dir / name, "an imported asset").write_bytes(blob)
    deck_md = confine.guard(out / "deck.md", "the imported deck")
    deck_md.write_text(md_writer.write(imp.deck), encoding="utf-8")
    back, back_issues = markdown_parser.parse(deck_md)
    mismatched = [n for n, (a, b) in enumerate(zip(imp.deck.slides, back.slides, strict=False), start=1) if a != b]
    confine.guard(report, "the import report")
    report.write_text(importer.report_md(src, brand, bool(args.adopt), imp, mismatched), encoding="utf-8")
    if back_issues or len(back.slides) != len(imp.deck.slides) or mismatched:
        if back_issues:
            detail = "; ".join(i.message for i in back_issues)
        elif len(back.slides) != len(imp.deck.slides):
            detail = f"{len(imp.deck.slides)} slides became {len(back.slides)} on reparse"
        else:
            detail = f"slide(s) {', '.join(map(str, mismatched))} differ after reparse"
        r.add(Issue("IMPORT_LOSSY", f"{deck_md.name} didn't reparse to the deck import produced: {detail}",
                    file=deck_md.name))
    unplaced = sum(len(x.unplaced) for x in imp.reports)
    dropped = sum(sum(x.dropped.values()) for x in imp.reports)
    r.data.update({"output": str(deck_md), "report": str(report), "brand": brand.slug, "slides": len(imp.reports),
                   "images": len(imp.assets), "unplaced": unplaced, "dropped": dropped,
                   "layouts": [{"slide": x.n, "layout": x.layout, "match": x.match} for x in imp.reports]})
    r.summary = (f"{'ok' if r.ok else 'failed'} import {src.name}: {len(imp.reports)} slides into {deck_md}, "
                 f"{len(imp.assets)} images, {unplaced} unplaced, {dropped} dropped formatting; read {report.name}")
    return r


def render_cmd(args: argparse.Namespace) -> Result:
    cfg = _cfg(args)
    pptx = Path(args.pptx)
    if pptx.suffix.lower() in pipeline.FORMATS or pptx.is_dir():
        raise EnvError(f"render takes a built .pptx, not {pptx.name}; run `deck-builder check {pptx} --render` "
                       "to build and render a deck in one step")
    if not pptx.is_file():
        raise EnvError(f"not found: {pptx}")
    if pptx.suffix.lower() != ".pptx":
        raise EnvError(f"render takes a .pptx file, not {pptx.suffix or 'a file with no extension'}")
    r = Result(command="render", data={"input": str(pptx)})
    _render_into(r, pptx, cfg, args.backend, _pages(args.slides), args.dpi)
    flagged = ", ".join(str(f["slide"]) for f in r.data["flagged_slides"]) or "none"
    hidden = ", ".join(str(n) for n in r.data["hidden_slides"]) or "none"
    r.summary = (f"{'ok' if r.ok else 'failed'} render {pptx.name} with {r.data['backend']}: flagged slides {flagged}; "
                 f"hidden slides {hidden}; "
                 f"contact sheets {', '.join(Path(p).name for p in r.data['contact_sheets'])} in "
                 f"{r.data['render_dir']}, {_tally(r)}")
    return r


def assets_cmd(args: argparse.Namespace) -> Result:
    cfg = _cfg(args)
    target = Path(args.target)
    r = Result(command="assets")
    if target.suffix.lower() in pipeline.FORMATS:
        loaded = pipeline.load_deck(target)
        brand = pipeline.brand_for(loaded.deck, target, cfg)
        items = asset_inventory.inventory_deck(loaded.deck, brand, target.parent)
        r.data.update({"deck": str(target), "brand": brand.slug})
    else:
        brand = registry.get(cfg, args.target)
        items = asset_inventory.inventory_brand(brand)
        r.data["brand"] = brand.slug
    r.data["assets"] = items
    for it in items:
        if it.get("unknown"):
            r.add(Issue("UNKNOWN_ASSET", f"{it['id']} isn't defined in brand {brand.slug!r}"))
        elif it.get("outside"):
            where = f"brand {brand.slug!r}'s kit" if str(it["id"]).startswith("brand:") else "the deck's folder"
            r.add(Issue("ASSET_OUTSIDE", f"{it['id']} resolves outside {where}"))
        elif it.get("missing"):
            r.add(Issue("MISSING_IMAGE", f"{it['id']}: {it['path']} not found"))
    lines = []
    for it in items:
        detail = it.get("value") or it.get("path", "")
        if "pixels" in it:
            detail += f" {it['pixels'][0]}x{it['pixels'][1]}"
        if "slides" in it:
            detail += f" slides {','.join(map(str, it['slides']))}"
        lines.append(f"{it['class']:<6} {it['id']:<28} {detail}")
    r.summary = "\n".join(lines) or "no assets"
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
    path = pipeline.deck_path(Path(args.deck))
    r = Result(command="check", data={"input": str(path)})
    if not args.render:
        deck, brand = _validated(path, cfg, r, args.brand)
        if deck is not None and brand is not None:
            r.data.update(_furniture(deck, brand))
        r.summary = f"{'ok' if r.ok else 'failed'} check {path.name}: {r.data['slides']} slides, {_tally(r)}"
        return r
    done = _build_one(path, cfg, args, None, None, r)
    if done:
        r.data.update(done)
        build_flags = [i for i in r.issues if i.slide is not None]  # e.g. ASSET_LOW_RES, raised at build
        _render_into(r, Path(done["output"]), cfg, args.backend, None)
        _merge_flagged_slides(r, build_flags)
    flagged = ", ".join(str(f["slide"]) for f in r.data.get("flagged_slides", [])) or "none"
    hidden = ", ".join(str(n) for n in r.data.get("hidden_slides", [])) or "none"
    r.summary = (f"{'ok' if r.ok else 'failed'} check --render {path.name}: {r.data['slides']} slides, "
                 f"flagged {flagged}, hidden {hidden}, {_tally(r)}")
    return r


def _merge_flagged_slides(r: Result, build_issues: list[Issue]) -> None:
    """check --render builds through the same path as build, so a build issue tied to a slide (such as
    ASSET_LOW_RES) belongs in flagged_slides beside whatever render found, not only in the issue list."""
    flagged: dict[int, list[str]] = {f["slide"]: list(f["codes"]) for f in r.data.get("flagged_slides", [])}
    for i in build_issues:
        assert i.slide is not None
        bucket = flagged.setdefault(i.slide, [])
        if i.code not in bucket:
            bucket.append(i.code)
    if flagged:
        r.data["flagged_slides"] = [{"slide": n, "codes": c} for n, c in sorted(flagged.items())]


def _furniture(deck: Deck, brand: Brand) -> dict[str, Any]:
    """Whether this deck's slides will show numbers, and the footer text they'll show (None for none)."""
    numbers, footer = furniture_settings(deck.meta)
    can = kit.furniture_layouts(brand)
    used = {s.layout for s in deck.slides}
    return {"slide_numbers": numbers and bool(used & set(can["slide_numbers"])),
            "footer": footer if footer and used & set(can["footer"]) else None}


def default_output(path: Path, deck: Deck | None, cfg: cfgmod.Config) -> Path:
    """-o wins (handled by the caller); then front matter `output`; then <workspace>/out/<name>.pptx.

    A file named deck.md or deck.xlsx takes its folder's name, so decks/q3/deck.md builds out/q3.pptx.
    """
    if deck is not None and deck.meta.get("output"):
        out = path.parent / str(deck.meta["output"])
        roots = [path.parent.resolve()] + ([(cfg.workspace / "out").resolve()] if cfg.found else [])
        if out.suffix.lower() != ".pptx" or not any(out.resolve().is_relative_to(r) for r in roots):
            raise EnvError(f"front matter output: {deck.meta['output']!r} must be a .pptx inside the deck's folder"
                           f"{' or the workspace out/ folder' if cfg.found else ''}")
        return out
    name = path.resolve().parent.name if path.stem == "deck" else path.stem
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
    manifest, issues = build_deck(deck, brand, path, out_path, _cache_dir(cfg), r.data["content_sha256"],
                                  force=getattr(args, "force", False))
    for i in issues:
        r.add(i)
    return {"output": str(out_path), "manifest": str(manifest_path(out_path)), "slides": len(manifest["slides"]),
            **_furniture(deck, brand)}


def build(args: argparse.Namespace) -> Result:
    cfg = _cfg(args)
    path = pipeline.deck_path(Path(args.deck))
    r = Result(command="build", data={"input": str(path)})
    if not args.data:
        out = Path(args.output) if args.output else None
        if out is not None and (out.is_dir() or args.output.endswith(("/", os.sep))):
            out = out / default_output(path, None, cfg).name  # -o a folder: the default name inside it
        elif out is not None and out.suffix.lower() != ".pptx":
            raise EnvError(f"-o takes a .pptx path or an existing folder, not {args.output!r}")
        done = _build_one(path, cfg, args, out, None, r)
        if done:
            r.data.update(done)
            r.summary = f"{'ok' if r.ok else 'failed'} build {done['output']}: {done['slides']} slides, {_tally(r)}"
        else:
            r.summary = f"failed build {path.name}: {_tally(r)}"
        return r

    rows = read_data_rows(Path(args.data))
    pattern = args.name or "{{_row}}.pptx"
    out_dir = Path(args.output) if args.output else default_output(path, None, cfg).with_suffix("")
    rows = [{**row, "_row": f"{n:03d}"} for n, row in enumerate(rows, start=1)]
    names = [_bulk_name(pattern, row) for row in rows]
    unresolved = [(n, cols) for n, (_, cols) in enumerate(names, start=1) if cols]
    if unresolved:
        detail = "; ".join(f"row {n}: {', '.join(sorted(set(cols)))}" for n, cols in unresolved)
        raise EnvError(f"--name {pattern!r} has a token with no matching column: {detail}")
    by_name: dict[str, list[int]] = {}
    for n, (name, _) in enumerate(names, start=1):
        by_name.setdefault(name.casefold(), []).append(n)
    dupes = {name: ns for name, ns in by_name.items() if len(ns) > 1}
    if dupes:
        detail = "; ".join(f"{names[ns[0] - 1][0]!r} from rows {', '.join(map(str, ns))}" for ns in dupes.values())
        raise EnvError(f"--name {pattern!r} gives more than one row the same output name: {detail}")
    built = []
    for n, row in enumerate(rows, start=1):
        name, _ = names[n - 1]
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
