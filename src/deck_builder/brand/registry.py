"""Find brand kits under brand_paths and load them. The registry is computed on every run."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from deck_builder import confine
from deck_builder.brand import schema
from deck_builder.config import Config
from deck_builder.errors import EnvError, Issue

HEX = re.compile(r"^#?[0-9A-Fa-f]{6}$")
TEMPLATE_NAMES = ("template.potx", "template.pptx")


@dataclass
class Brand:
    slug: str
    path: Path
    meta: dict[str, Any] = field(default_factory=dict)  # brand.yaml
    tokens: dict[str, Any] = field(default_factory=dict)  # tokens.yaml
    template: Path | None = None
    problems: list[str] = field(default_factory=list)  # missing files, unreadable YAML
    schema_errors: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return str(self.meta.get("name", self.slug))

    @property
    def version(self) -> str:
        return str(self.meta.get("version", "0.0.0"))

    @property
    def valid(self) -> bool:
        return not self.problems and not self.schema_errors

    def color(self, ref: str | None) -> str | None:
        """A palette name or a hex value -> 6-digit uppercase hex; None if unknown."""
        if ref is None:
            return None
        palette = self.meta.get("palette") or {}
        if ref in palette:
            ref = str(palette[ref])
        ref = str(ref)
        return ref.lstrip("#").upper() if HEX.match(ref) else None

    def layout_names(self) -> list[str]:
        return list((self.tokens.get("layouts") or {}).keys())


def _duplicate_idx_problems(tokens: dict[str, Any]) -> list[str]:
    """Two fields naming the same placeholder idx in one layout would fill, then clear, one placeholder."""
    problems: list[str] = []
    for lname, ls in (tokens.get("layouts") or {}).items():
        if not isinstance(ls, dict):
            continue
        by_idx: dict[Any, list[str]] = {}
        for fname, fs in (ls.get("fields") or {}).items():
            if isinstance(fs, dict) and "idx" in fs:
                by_idx.setdefault(fs["idx"], []).append(fname)
        for idx, fnames in by_idx.items():
            if len(fnames) > 1:
                problems.append(f"layout {lname!r}: fields {', '.join(sorted(fnames))} share placeholder "
                                f"idx {idx!r}; give each field its own idx")
    return problems


def _load_yaml(path: Path, problems: list[str]) -> dict[str, Any]:
    if not path.is_file():
        problems.append(f"missing {path.name}")
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        problems.append(f"{path.name}: invalid YAML: {e}")
        return {}
    if not isinstance(data, dict):
        problems.append(f"{path.name}: must be a mapping")
        return {}
    return data


def load_kit(path: Path) -> Brand:
    problems: list[str] = []
    meta = _load_yaml(path / "brand.yaml", problems)
    tokens = _load_yaml(path / "tokens.yaml", problems)
    present = [n for n in TEMPLATE_NAMES if (path / n).is_file()]
    template = path / present[0] if present else None
    if not present:
        problems.append("missing template.potx or template.pptx")
    elif len(present) > 1:
        problems.append(f"both {present[0]} and {present[1]} are in this kit; keep the one this kit actually "
                        f"uses and remove the other (brand init writes template.potx, adopt writes "
                        "template.pptx; a kit never needs both)")
    slug = str(meta.get("slug") or path.name)
    if meta and slug != path.name:
        problems.append(f"slug {slug!r} doesn't match folder name {path.name!r}")
    schema_errors = (schema.errors("brand", meta) if meta else []) + (schema.errors("tokens", tokens) if tokens else [])
    if tokens and not schema_errors:
        problems += _duplicate_idx_problems(tokens)
    return Brand(slug=slug, path=path, meta=meta, tokens=tokens, template=template, problems=problems,
                 schema_errors=schema_errors)


def discover(cfg: Config) -> tuple[dict[str, Brand], list[Issue]]:
    found: dict[str, Brand] = {}
    issues: list[Issue] = []
    for root in cfg.brand_paths:
        if not root.is_dir():
            continue
        candidates = [root] if (root / "brand.yaml").is_file() else sorted(
            p for p in root.iterdir() if p.is_dir() and (p / "brand.yaml").is_file()
        )
        for kit in candidates:
            try:
                # a candidate folder name under brand_paths can already be an existing symlink
                # pointing outside every allowed root; skip it rather than load a kit from there
                # (a no-op outside an MCP call, which has no allowed-root list to check against).
                confine.guard(kit, "a brand kit folder")
            except EnvError:
                continue
            b = load_kit(kit)
            if b.slug in found:
                issues.append(Issue("BRAND_DUPLICATE",
                                    f"slug {b.slug!r} at {found[b.slug].path} and {b.path}"))
                continue
            found[b.slug] = b
    return found, issues


def get(cfg: Config, slug: str) -> Brand:
    brands, issues = discover(cfg)
    dup = [i for i in issues if f"{slug!r}" in i.message]
    if dup:
        raise EnvError(dup[0].message, code="BRAND_DUPLICATE")
    if slug not in brands:
        known = ", ".join(sorted(brands)) or "none"
        hint = "" if cfg.found else ("; no deck-builder.toml in this folder or above it, so run "
                                     "`deck-builder init` here or pass --config")
        raise EnvError(f"no brand {slug!r} under brand_paths (found: {known}){hint}", code="UNKNOWN_BRAND")
    return brands[slug]


def explicit(template: Path, tokens: Path) -> Brand:
    """A deck that names template and tokens files directly, with no brand.yaml."""
    problems: list[str] = []
    data = _load_yaml(tokens, problems)
    if not template.is_file():
        problems.append(f"template not found: {template}")
    schema_errors = schema.errors("tokens", data) if data else []
    if data and not schema_errors:
        problems += _duplicate_idx_problems(data)
    return Brand(slug="(explicit)", path=tokens.parent, meta={}, tokens=data, template=template,
                 problems=problems, schema_errors=schema_errors)
