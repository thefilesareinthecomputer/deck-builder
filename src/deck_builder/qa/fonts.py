"""Which fonts the renderer actually used, against the fonts the brand specifies."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from deck_builder.errors import Issue


def squash(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def embedded(pdf: Path) -> set[str]:
    """Font names in the PDF, subset prefixes (ABCDEF+) removed, squashed for comparison."""
    out = subprocess.run(["pdffonts", str(pdf.resolve())], capture_output=True, text=True, check=True,
                         timeout=60).stdout
    names = set()
    for line in out.splitlines()[2:]:
        if line.strip():
            names.add(squash(line.split()[0].split("+")[-1]))
    return names


def check(pdf: Path, brand_meta: dict[str, Any]) -> list[Issue]:
    used = embedded(pdf)
    issues = []
    for role, font in (brand_meta.get("fonts") or {}).items():
        family = font.get("family", "")
        fallback = font.get("fallback")
        if any(u.startswith(squash(family)) for u in used):
            continue
        if fallback and any(u.startswith(squash(fallback)) for u in used):
            issues.append(Issue("MISSING_FONT", f"{role} font {family!r} rendered with its fallback {fallback!r}",
                                severity="warning"))
            continue
        issues.append(Issue("MISSING_FONT", f"{role} font {family!r} isn't installed here; the renderer substituted "
                                            f"({', '.join(sorted(used)) or 'no fonts found'})", severity="warning"))
    return issues
