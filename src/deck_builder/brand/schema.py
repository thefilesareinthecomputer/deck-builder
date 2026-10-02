"""JSON Schema validation for brand.yaml, tokens.yaml and manifests. Every violation is reported."""
from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator

NAMES = ("brand", "tokens", "manifest")


@cache
def load(name: str) -> dict[str, Any]:
    text = resources.files("deck_builder").joinpath("schemas", f"{name}.schema.json").read_text(encoding="utf-8")
    return dict(json.loads(text))


def errors(name: str, data: Any) -> list[str]:
    """Every violation as 'path: message', sorted for stable output."""
    validator = Draft202012Validator(load(name))
    out = []
    for e in validator.iter_errors(data):
        where = ".".join(str(p) for p in e.absolute_path) or "(top level)"
        out.append(f"{name}.yaml {where}: {e.message}")
    return sorted(out)
