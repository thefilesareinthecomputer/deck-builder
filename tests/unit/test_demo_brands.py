"""The demo-brands fixtures: one showcase deck bulk-builds into three generated brands."""
from pathlib import Path

import pytest

from conftest import cli_json

DEMO = Path(__file__).resolve().parents[1] / "fixtures" / "demo-brands"
SLUGS = ("briarfield-paper", "cubicle-nine", "afterhours-soap")


@pytest.fixture(scope="module")
def demo_ws(tmp_path_factory):
    from deck_builder.cli import main

    root = tmp_path_factory.mktemp("demo")
    assert main(["init", "--dir", str(root)]) == 0
    for slug in SLUGS:
        args = ["--config", str(root / "deck-builder.toml"), "brand", "init", slug,
                "--from", str(DEMO / "brands" / slug / "brand.yaml")]
        assert main(args) == 0, slug
    return root


def test_showcase_builds_clean_in_all_three_brands(demo_ws, capsys):
    capsys.readouterr()
    code, out = cli_json(demo_ws, "build", str(DEMO / "showcase" / "deck.md"),
                         "--data", str(DEMO / "showcase" / "brands.csv"), "--name", "{{brand}}.pptx",
                         "-o", str(demo_ws / "showcase"), capsys=capsys)
    assert code == 0, out["issues"]
    assert [i for i in out["issues"] if i["severity"] == "error"] == []
    assert sorted(Path(o["output"]).name for o in out["outputs"]) == sorted(f"{s}.pptx" for s in SLUGS)
