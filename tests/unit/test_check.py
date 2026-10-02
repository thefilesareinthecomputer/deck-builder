from pathlib import Path

import pytest

from conftest import cli_json, codes, make_kit, write_deck

GOOD = """
---
title: Pemberton Paper quarterly review
brand: stock
---

## Pemberton Paper quarterly review
layout: title
subtitle: Shipments, margins and next quarter

## Paper volume grew 12% in Q3
layout: content

- Copy paper led the growth
  - Two new regional accounts
- **Card stock** held flat

Notes:
Source: Q3 shipment ledger.

## 12%
layout: big-number
caption: Volume growth, Q2 to Q3

## Volume by product
layout: chart

```chart
type: column
categories: [Jul, Aug, Sep]
series:
  - name: Copy paper
    values: [410, 378, 331]
```

## Open items
layout: table

| Item | Owner | Due |
|---|---|---|
| Warehouse lease | Ops | Oct |

## Logo
layout: image

![Logo](brand:logo/primary)

### caption
The current mark.

## Checked
layout: icon
icon: brand:icon/check
"""


def test_valid_deck_passes(ws, capsys):
    code, out = cli_json(ws, "check", str(write_deck(ws, GOOD)), capsys=capsys)
    assert code == 0, out["issues"]
    assert out["ok"] is True
    assert out["slides"] == 7
    assert out["brand"] == "stock"


def test_check_render_flags_a_build_time_low_res_warning(ws, capsys, monkeypatch):
    from deck_builder import commands
    from deck_builder.qa.render import Rendered

    def fake_render(pptx, backend, dpi, batch, pages, brand):
        out_dir = pptx.with_name(pptx.stem + ".render")
        out_dir.mkdir(exist_ok=True)
        pdf = out_dir / "deck.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")
        return Rendered(backend="stub", out_dir=out_dir, pdf=pdf, slides=[], contact_sheets=[], issues=[])

    monkeypatch.setattr(commands.qa_backends, "choose", lambda requested: "stub")
    monkeypatch.setattr(commands.qa_render, "render", fake_render)
    code, out = cli_json(ws, "check", str(write_deck(ws, GOOD)), "--render", capsys=capsys)
    assert code == 0, out["issues"]  # ASSET_LOW_RES is a warning, build still succeeds
    assert "ASSET_LOW_RES" in codes(out)
    flagged = {f["slide"]: f["codes"] for f in out["flagged_slides"]}
    assert 7 in flagged and "ASSET_LOW_RES" in flagged[7]


def test_render_with_a_malformed_manifest_renders_without_a_brand_instead_of_crashing(ws, capsys, monkeypatch):
    from deck_builder import commands
    from deck_builder.qa.render import Rendered

    code, out = cli_json(ws, "build", str(write_deck(ws, GOOD)), capsys=capsys)
    assert code == 0, out["issues"]
    Path(out["manifest"]).write_text('{"not": "a real manifest"}', encoding="utf-8")

    def fake_render(pptx, backend, dpi, batch, pages, brand):
        assert brand is None  # a manifest with no brand.slug is treated like no manifest at all
        out_dir = pptx.with_name(pptx.stem + ".render")
        out_dir.mkdir(exist_ok=True)
        pdf = out_dir / "deck.pdf"
        pdf.write_bytes(b"%PDF-1.4 stub")
        return Rendered(backend="stub", out_dir=out_dir, pdf=pdf, slides=[], contact_sheets=[], issues=[])

    monkeypatch.setattr(commands.qa_backends, "choose", lambda requested: "stub")
    monkeypatch.setattr(commands.qa_render, "render", fake_render)
    code, out = cli_json(ws, "render", out["output"], capsys=capsys)
    assert code == 0, out


def test_human_output_is_one_summary_line(ws, capsys):
    from deck_builder.cli import main

    code = main(["--config", str(ws / "deck-builder.toml"), "check", str(write_deck(ws, GOOD))])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 0
    assert out == ["ok check deck.md: 7 slides, 0 errors, 0 warnings"]


@pytest.mark.parametrize("body, expected", [
    ("## A\nlayout: nope\n", "UNKNOWN_LAYOUT"),
    ("## A\nlayout: title\nmood: sunny\n", "UNKNOWN_FIELD"),
    ("## 5\nlayout: big-number\n", "MISSING_FIELD"),
    ("## A\nlayout: chart\n\n- not a chart\n", "KIND_MISMATCH"),
    ("## " + "x" * 61 + "\nlayout: title\n", "BUDGET_CHARS"),
    ("## A\nlayout: content\n\n" + "".join(f"- b{i}\n" for i in range(6)), "BUDGET_BULLETS"),
    ("## A\nlayout: content\n\n- " + "y" * 81 + "\n", "BUDGET_BULLET_CHARS"),
    ("## A\nlayout: content\n\n- a\n  - b\n    - c\n", "BUDGET_LEVEL"),
    ("## A\nlayout: table\n\n| a | b |\n|---|---|\n| 1 |\n", "TABLE_SHAPE"),
    ("## A\nlayout: chart\n\n```chart\ntype: radar\ncategories: [a]\nseries: [{name: s, values: [1]}]\n```\n",
     "CHART_SHAPE"),
    ("## A\nlayout: image\n\n![x](assets/missing.png)\n", "MISSING_IMAGE"),
    ("## A\nlayout: image\n\n![x](assets/diagram.svg)\n", "ASSET_FORMAT"),
    ("## A\nlayout: image\n\n![x](brand:logo/nope)\n", "UNKNOWN_ASSET"),
    ("## A\nlayout: icon\nicon: brand:icon/nope\n", "UNKNOWN_ASSET"),
    ("## Real synergy here\nlayout: title\n", "BANNED_PATTERN"),
    ("## A\nlayout: title\n\nNotes:\nAn em dash — here\n", "BANNED_PATTERN"),
    ("".join(f"## S{i}\nlayout: title\n\n" for i in range(13)), "MAX_SLIDES"),
    ("## A\nlayout: chart\n\n```chart\ntype: [unclosed\n```\n", "PARSE"),
    ("no headings at all\n", "PARSE"),
])
def test_each_issue_code(ws, capsys, body, expected):
    deck = write_deck(ws, "---\nbrand: stock\n---\n\n" + body)
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert code == 1
    assert expected in codes(out), out["issues"]


def test_spec_version_newer_than_engine(ws, capsys):
    deck = write_deck(ws, "---\nspec_version: 99\n---\n\n## A\nlayout: title\n")
    _, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert "SPEC_VERSION" in codes(out)


def test_issue_reports_file_line_slide_and_field(ws, capsys):
    deck = write_deck(ws, "---\nbrand: stock\n---\n\n## Fine\nlayout: title\n\n## A\nlayout: title\nmood: x\n")
    _, out = cli_json(ws, "check", str(deck), capsys=capsys)
    issue = out["issues"][0]
    assert (issue["file"], issue["line"], issue["slide"], issue["field"]) == ("deck.md", 8, 2, "mood")


def test_template_mismatch(ws, capsys):
    tokens = ws / "brands" / "stock" / "tokens.yaml"
    tokens.write_text(tokens.read_text().replace("Two Content", "Three Content"))
    deck = write_deck(ws, "## A\nlayout: two-col\n\n### left\n- x\n")
    _, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert "TEMPLATE_MISMATCH" in codes(out)


def test_unknown_brand_is_an_environment_error(ws, capsys):
    deck = write_deck(ws, "---\nbrand: nope\n---\n\n## A\nlayout: title\n")
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert code == 2
    assert out["code"] == "UNKNOWN_BRAND"


def test_duplicate_brand_slugs(ws, capsys):
    other = ws / "more-brands"
    make_kit(other)
    cfg = ws / "deck-builder.toml"
    cfg.write_text(cfg.read_text().replace('["brands"]', '["brands", "more-brands"]'))
    code, out = cli_json(ws, "check", str(write_deck(ws, GOOD)), capsys=capsys)
    assert code == 2
    assert out["code"] == "BRAND_DUPLICATE"


def test_broken_kit_reports_brand_invalid(ws, capsys):
    (ws / "brands" / "stock" / "template.pptx").unlink()
    code, out = cli_json(ws, "check", str(write_deck(ws, GOOD)), capsys=capsys)
    assert code == 1
    assert "BRAND_INVALID" in codes(out)


def test_csv_input_and_sheet_refs(ws, capsys):
    p = ws / "decks" / "slides.csv"
    p.write_text('layout,title,subtitle,body,chart\ntitle,Hello,World,,\n'
                 'content,Points,,"- one\n- two",\nchart,Trend,,,sheet:chart-3\n', encoding="utf-8")
    code, out = cli_json(ws, "check", str(p), capsys=capsys)
    assert codes(out) == ["CSV_NO_SHEETS", "MISSING_FIELD"]


def test_bulk_tokens(tmp_path):
    from deck_builder.parse import markdown

    p = tmp_path / "t.md"
    p.write_text("## {{client}} review\nlayout: title\nsubtitle: For {{contact}}\n")
    deck, issues = markdown.parse(p, {"client": "Halvorsen", "contact": "Ops"})
    assert issues == []
    assert (deck.slides[0].title, deck.slides[0].fields["subtitle"]) == ("Halvorsen review", "For Ops")


def test_bulk_unknown_token_stops_the_parse(tmp_path):
    from deck_builder.parse import markdown

    p = tmp_path / "t.md"
    p.write_text("## {{client}} review\nlayout: title\nsubtitle: {{nope}}\n")
    deck, issues = markdown.parse(p, {"client": "Halvorsen"})
    assert [i.code for i in issues] == ["UNKNOWN_TOKEN"]
    assert deck.slides == []
