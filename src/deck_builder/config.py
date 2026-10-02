"""Config resolution: --config, $DECK_BUILDER_CONFIG, nearest deck-builder.toml, user config, defaults."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from deck_builder.errors import EnvError

FILENAME = "deck-builder.toml"
USER_CONFIG = Path("~/.config/deck-builder/config.toml")
ENV_VAR = "DECK_BUILDER_CONFIG"


@dataclass
class RenderConfig:
    backend: str = "auto"
    dpi: int = 96
    contact_batch: int = 20


@dataclass
class Config:
    path: Path | None  # None when built-in defaults are in use
    root: Path  # paths in the config resolve against this directory
    workspace: Path
    brand_paths: list[Path]
    default_brand: str | None = None
    render: RenderConfig = field(default_factory=RenderConfig)

    @property
    def found(self) -> bool:
        return self.path is not None


def _resolve(root: Path, p: str) -> Path:
    q = Path(p).expanduser()
    return q if q.is_absolute() else (root / q)


def _widens_reach(full: Path, root: Path) -> str | None:
    """A reason this brand_paths entry would widen the MCP server's reach, or None if it's fine."""
    if full == Path.home().resolve():
        return "the user's home folder"
    if full.parent == full:  # a filesystem root such as / or C:\
        return "the filesystem root"
    if full == root or full in root.parents:
        return "the config folder or one of its ancestors"
    return None


def _brand_path(root: Path, path: Path, entry: str) -> Path:
    full = _resolve(root, entry)
    reason = _widens_reach(full.resolve(), root)
    if reason is not None:
        raise EnvError(f"{path}: brand_paths entry {entry!r} resolves to {reason}; use a folder dedicated to "
                       "brand kits")
    return full


def _find_upward(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        cand = d / FILENAME
        if cand.is_file():
            return cand
    return None


def locate(explicit: str | None, cwd: Path) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_file():
            raise EnvError(f"config file not found: {p}")
        return p
    env = os.environ.get(ENV_VAR)
    if env:
        p = Path(env).expanduser()
        if not p.is_file():
            raise EnvError(f"{ENV_VAR} points at a missing file: {p}")
        return p
    found = _find_upward(cwd.resolve())
    if found:
        return found
    user = USER_CONFIG.expanduser()
    return user if user.is_file() else None


def load(explicit: str | None = None, cwd: Path | None = None) -> Config:
    cwd = cwd or Path.cwd()
    path = locate(explicit, cwd)
    if path is None:
        root = cwd.resolve()
        ws = root / "workspace"
        return Config(path=None, root=root, workspace=ws, brand_paths=[ws / "brands"])
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise EnvError(f"{path}: invalid TOML: {e}") from e
    root = path.parent.resolve()
    ws = _resolve(root, str(raw.get("workspace", "workspace")))
    brand_paths = [_brand_path(root, path, str(p)) for p in raw.get("brand_paths", [str(ws / "brands")])]
    r = raw.get("render", {}) or {}
    render = RenderConfig(
        backend=str(r.get("backend", "auto")),
        dpi=int(r.get("dpi", 96)),
        contact_batch=int(r.get("contact_batch", 20)),
    )
    if render.backend not in ("auto", "powerpoint", "libreoffice"):
        raise EnvError(f"{path}: render.backend must be auto, powerpoint or libreoffice")
    return Config(
        path=path,
        root=root,
        workspace=ws,
        brand_paths=brand_paths,
        default_brand=raw.get("default_brand"),
        render=render,
    )
