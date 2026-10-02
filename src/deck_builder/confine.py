"""One confinement check for paths derived after an MCP argument was already validated.

`mcp.Server.call` checks each argument path before a command runs (see `mcp._path`), but a command
then derives further paths from it: a manifest beside a build output, a render folder beside a
.pptx, a brand slug appended to a brand_paths root, a deck file found inside a folder argument, a
kit folder discovered under brand_paths. Each of those can already be an existing symlink pointing
outside every allowed root, so checking only the original argument doesn't confine what's built
from it. `guard` is the one check used at every such point, right before the path is read, written
or deleted.

Outside an MCP call `active()` is unset and `guard` does nothing, so the plain CLI keeps working for
any path a user passes directly - there's no "workspace" to confine a local, trusted invocation to.
"""
from __future__ import annotations

import contextlib
from collections.abc import Iterator
from contextvars import ContextVar
from pathlib import Path

from deck_builder.errors import EnvError

_roots: ContextVar[tuple[Path, ...] | None] = ContextVar("deck_builder_confine_roots", default=None)


@contextlib.contextmanager
def scoped(*roots: Path) -> Iterator[None]:
    """While the block runs, `guard` refuses any path outside these roots."""
    token = _roots.set(tuple(r.resolve() for r in roots))
    try:
        yield
    finally:
        _roots.reset(token)


def active() -> tuple[Path, ...] | None:
    return _roots.get()


def guard(path: Path, what: str = "path") -> Path:
    """Inside a `scoped` block, resolve path (following symlinks) and refuse one outside its roots.

    Returns path unchanged - this only ever narrows what's allowed, never what a caller sees. A
    no-op outside `scoped` (plain CLI use): there's nothing to resolve or compare against, so a
    path a CLI user passes directly is never even touched. Call this at the point of use, not only
    when a path argument is first accepted: anything appended or derived afterward needs the same
    check again.
    """
    roots = _roots.get()
    if roots is None:
        return path
    resolved = path.resolve()
    if not any(resolved.is_relative_to(r) for r in roots):
        raise EnvError(f"{what} {path} resolves outside the allowed area; refusing to use it")
    return path
