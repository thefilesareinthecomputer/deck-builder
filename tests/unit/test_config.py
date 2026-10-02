"""Loading deck-builder.toml: brand_paths entries that would widen the MCP server's reach."""
from pathlib import Path

import pytest

from deck_builder import config as cfgmod
from deck_builder.errors import EnvError


def write_toml(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "deck-builder.toml"
    p.write_text(body, encoding="utf-8")
    return p


@pytest.mark.parametrize("entry, reason", [
    ("~", "the user's home folder"),
    ("/", "the filesystem root"),
    (".", "the config folder or one of its ancestors"),
    ("..", "the config folder or one of its ancestors"),
])
def test_a_widening_brand_paths_entry_is_refused(tmp_path, entry, reason):
    cfg = write_toml(tmp_path, f'brand_paths = ["{entry}"]\n')
    with pytest.raises(EnvError, match=reason) as exc:
        cfgmod.load(str(cfg))
    assert repr(entry) in str(exc.value)


def test_brand_paths_inside_or_beside_the_config_folder_load(tmp_path):
    cfg = write_toml(tmp_path, 'brand_paths = ["workspace/brands", "../other-repo/brands"]\n')
    loaded = cfgmod.load(str(cfg))
    assert loaded.brand_paths[0] == tmp_path / "workspace" / "brands"
    assert loaded.brand_paths[1] == tmp_path / ".." / "other-repo" / "brands"


def test_the_default_brand_paths_entry_is_never_refused(tmp_path):
    cfg = write_toml(tmp_path, 'workspace = "."\n')
    loaded = cfgmod.load(str(cfg))
    assert loaded.brand_paths == [tmp_path / "brands"]


@pytest.mark.parametrize("entry, reason", [
    ("~", "the user's home folder"),
    ("/", "the filesystem root"),
    ("..", "the config folder or one of its ancestors"),
])
def test_a_widening_workspace_value_is_refused(tmp_path, entry, reason):
    cfg = write_toml(tmp_path, f'workspace = "{entry}"\n')
    with pytest.raises(EnvError, match=reason) as exc:
        cfgmod.load(str(cfg))
    assert repr(entry) in str(exc.value)


def test_workspace_equal_to_the_config_folder_loads(tmp_path):
    cfg = write_toml(tmp_path, 'workspace = "."\n')
    loaded = cfgmod.load(str(cfg))
    assert loaded.workspace == tmp_path
