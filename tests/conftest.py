"""Shared fixtures. Every test works in a temp dir; nothing touches the real workspace."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
import yaml
from PIL import Image
from pptx import Presentation

from deck_builder.cli import main

# Maps logical layouts onto python-pptx's stock template, which every machine has.
STOCK_TOKENS = {
    "spec_version": 1,
    "chart": {"colors": ["primary", "accent"]},
    "table": {"header_fill": "primary", "header_text": "background"},
    "layouts": {
        "title": {"template_layout": "Title Slide", "fields": {
            "title": {"idx": 0, "kind": "text", "max_chars": 60, "required": True},
            "subtitle": {"idx": 1, "kind": "text", "max_chars": 110}}},
        "content": {"template_layout": "Title and Content", "fields": {
            "title": {"idx": 0, "kind": "text", "max_chars": 70, "required": True},
            "body": {"idx": 1, "kind": "bullets", "max_chars": 300, "max_bullets": 5,
                     "max_bullet_chars": 80, "max_level": 1}}},
        "two-col": {"template_layout": "Two Content", "fields": {
            "title": {"idx": 0, "kind": "text", "max_chars": 70, "required": True},
            "left": {"idx": 1, "kind": "bullets", "max_chars": 200},
            "right": {"idx": 2, "kind": "bullets", "max_chars": 200}}},
        "big-number": {"template_layout": "Section Header", "heading_field": "number", "fields": {
            "number": {"idx": 0, "kind": "text", "max_chars": 8, "required": True},
            "caption": {"idx": 1, "kind": "text", "max_chars": 90, "required": True}}},
        "chart": {"template_layout": "Title and Content", "fields": {
            "title": {"idx": 0, "kind": "text", "max_chars": 70, "required": True},
            "chart": {"idx": 1, "kind": "chart", "required": True}}},
        "table": {"template_layout": "Title and Content", "fields": {
            "title": {"idx": 0, "kind": "text", "max_chars": 70, "required": True},
            "table": {"idx": 1, "kind": "table", "max_rows": 4, "max_cols": 3, "required": True}}},
        "image": {"template_layout": "Picture with Caption", "fields": {
            "title": {"idx": 0, "kind": "text", "max_chars": 50, "required": True},
            "image": {"idx": 1, "kind": "image", "required": True},
            "caption": {"idx": 2, "kind": "text", "max_chars": 120}}},
        "icon": {"template_layout": "Picture with Caption", "fields": {
            "title": {"idx": 0, "kind": "text", "max_chars": 50, "required": True},
            "icon": {"idx": 1, "kind": "icon", "required": True},
            "caption": {"idx": 2, "kind": "text", "max_chars": 120}}},
    },
}

STOCK_BRAND = {
    "spec_version": 1,
    "name": "Stock Test Brand",
    "slug": "stock",
    "version": "1.0.0",
    "palette": {"primary": "1F3A5F", "accent": "E07A2F", "ink": "1B1B1B", "background": "FFFFFF"},
    "fonts": {"heading": {"family": "Arial"}, "body": {"family": "Arial"}},
    "logos": {"primary": "assets/logo.png"},
    "icons": {"dir": "assets/icons", "default_color": "accent", "source": "test fixture"},
    "lint": {"max_slides": 12, "banned_patterns": ["—", "(?i)\\bsynerg"]},
}


def make_kit(root: Path, slug: str = "stock") -> Path:
    kit = root / slug
    (kit / "assets" / "icons").mkdir(parents=True)
    Presentation().save(str(kit / "template.pptx"))
    meta = {**STOCK_BRAND, "slug": slug}
    (kit / "brand.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    (kit / "tokens.yaml").write_text(yaml.safe_dump(STOCK_TOKENS, sort_keys=False), encoding="utf-8")
    Image.new("RGB", (400, 200), "#1F3A5F").save(kit / "assets" / "logo.png")
    Image.new("RGBA", (128, 128), (0, 0, 0, 255)).save(kit / "assets" / "icons" / "check.png")
    return kit


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    """A project root with deck-builder.toml, brands/stock and an empty decks/ folder."""
    make_kit(tmp_path / "brands")
    (tmp_path / "decks").mkdir()
    (tmp_path / "deck-builder.toml").write_text(
        'workspace = "."\nbrand_paths = ["brands"]\ndefault_brand = "stock"\n', encoding="utf-8")
    return tmp_path


def write_deck(ws: Path, body: str, name: str = "deck.md") -> Path:
    p = ws / "decks" / name
    p.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return p


def cli_json(ws: Path, *argv: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict]:
    code = main(["--config", str(ws / "deck-builder.toml"), *argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def codes(payload: dict) -> list[str]:
    return [i["code"] for i in payload["issues"]]
