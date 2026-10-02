"""Command handlers. Each takes parsed args and returns a Result; cli.py prints it."""
from __future__ import annotations

import argparse
from pathlib import Path

from deck_builder import config as cfgmod
from deck_builder import docs, pipeline, validate
from deck_builder.errors import CODES, EnvError, Issue, Result


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


def check(args: argparse.Namespace) -> Result:
    cfg = _cfg(args)
    path = Path(args.deck)
    r = Result(command="check", data={"input": str(path)})
    loaded = pipeline.load_deck(path)
    for i in loaded.issues:
        r.add(i)
    brand = pipeline.brand_for(loaded.deck, path, cfg, getattr(args, "brand", None))
    r.data["brand"] = brand.slug
    for p in brand.problems:
        r.add(Issue("BRAND_INVALID", f"brand {brand.slug!r}: {p}"))
    if brand.valid:
        _, issues = validate.resolve(loaded.deck, brand, path.parent)
        for i in issues:
            r.add(i)
    r.data["slides"] = len(loaded.deck.slides)
    r.summary = f"{'ok' if r.ok else 'failed'} check {path.name}: {len(loaded.deck.slides)} slides, {_tally(r)}"
    return r
