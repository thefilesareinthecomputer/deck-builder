"""Slide text checks and tools: SLIDE_REF, INVISIBLE_CHAR and `fix-text`, inline code in BUDGET_LINES, the
layouts a budget issue names, `inspect --text` and `--index`, code fonts on import, and why slide numbers are off."""
from pathlib import Path

import yaml
from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.oxml.ns import qn

from conftest import cli_json, codes, write_deck
from deck_builder import importer, validate
from deck_builder.cli import main

NBSP, ZWSP, SMILEY = chr(0xA0), chr(0x200B), chr(0xF04A)  # SMILEY: the symbol-font glyph PowerPoint makes from ":)"


def _issues(out: dict, code: str) -> list[dict]:
    return [i for i in out["issues"] if i["code"] == code]


def test_slide_ref_warns_on_a_slide_named_by_position_in_text_and_notes(ws, capsys):
    p = write_deck(ws, """
        ## Orders ship the same day
        layout: content

        - As the next slide shows, most orders ship by four
        - The `slide 3` key and the "previous slide" quote are someone else's words
        - The last slide deck we sent had the old prices

        Notes:
        We cover returns on slide 12.
        """)
    code, out = cli_json(ws, "check", str(p), capsys=capsys)
    assert code == 0  # a warning
    hits = _issues(out, "SLIDE_REF")
    assert [(h["field"], h["severity"]) for h in hits] == [("body", "warning"), ("notes", "warning")]
    assert "'next slide'" in hits[0]["message"] and "quote" not in hits[0]["message"]
    assert "the speaker notes" in hits[1]["message"] and "'slide 12'" in hits[1]["message"]


def test_invisible_char_names_each_character_and_where_it_is(ws, capsys):
    p = write_deck(ws, f"""
        ## Orders ship{NBSP}the same day
        layout: content

        - Most orders ship by four{ZWSP}

        Notes:
        Thanks, team {SMILEY}
        """)
    code, out = cli_json(ws, "check", str(p), capsys=capsys)
    assert code == 0
    by_field = {h["field"]: h["message"] for h in _issues(out, "INVISIBLE_CHAR")}
    assert "U+00A0 NO-BREAK SPACE" in by_field["title"]
    assert "U+200B ZERO WIDTH SPACE" in by_field["body"]
    assert "U+F04A PRIVATE-USE CHARACTER" in by_field["notes"] and "fix-text" in by_field["notes"]


def test_fix_text_replaces_them_and_keeps_everything_else_byte_for_byte(ws, capsys):
    p = ws / "decks" / "draft.md"
    p.write_bytes(f"a{NBSP}b{NBSP}c\r\nplain line\r\nsmile {SMILEY}{ZWSP}\n".encode())
    code = main(["fix-text", str(p)])
    said = capsys.readouterr().out
    assert code == 0
    assert p.read_bytes() == b"a b c\r\nplain line\r\nsmile \n"
    assert "line 1: U+00A0 NO-BREAK SPACE (2)" in said and "line 3: " in said and "line 2" not in said
    assert "fixed 4 characters on 2 lines of draft.md" in said
    assert main(["fix-text", str(p)]) == 0 and "nothing to fix in draft.md" in capsys.readouterr().out


def test_fix_text_takes_a_deck_folder_and_refuses_a_workbook(ws, capsys):
    folder = ws / "decks" / "q3"
    folder.mkdir()
    (folder / "deck.md").write_text(f"## A{NBSP}title\n", encoding="utf-8")
    code, out = cli_json(ws, "fix-text", str(folder), capsys=capsys)
    assert code == 0 and out["changes"] == [{"line": 1, "chars": {"U+00A0 NO-BREAK SPACE": 1}}]
    (folder / "deck.xlsx").write_bytes(b"PK")
    code, out = cli_json(ws, "fix-text", str(folder / "deck.xlsx"), capsys=capsys)
    assert code == 2 and "Excel" in out["error"]


def test_inline_code_counts_at_the_code_fonts_width_when_wrapping():
    assert validate.CODE_WIDTH > 1.2
    assert validate.word_widths("see **the** `ab` table") == [3, 3, 2 * validate.CODE_WIDTH, 5]
    assert validate._wrapped("abcdefgh x", 10) == 1
    assert validate._wrapped("`abcdefgh` x", 10) == 2  # eight code characters are wider than ten body ones


def test_budget_lines_says_how_far_over_it_is(ws, capsys):
    tokens = ws / "brands" / "stock" / "tokens.yaml"
    t = yaml.safe_load(tokens.read_text())
    t["layouts"]["content"]["fields"]["body"].update(line_chars=20, max_lines=2, max_bullet_chars=200)
    tokens.write_text(yaml.safe_dump(t))
    p = write_deck(ws, """
        ## Orders ship the same day
        layout: content

        Most orders ship by four in the afternoon from the main warehouse.
        """)
    code, out = cli_json(ws, "check", str(p), capsys=capsys)
    hit = _issues(out, "BUDGET_LINES")[0]
    assert "the box holds 2, so about" in hit["message"] and "characters too many" in hit["message"]


def test_a_budget_issue_names_the_layouts_that_hold_the_text_as_written(ws, capsys):
    tokens = ws / "brands" / "stock" / "tokens.yaml"
    t = yaml.safe_load(tokens.read_text())
    t["layouts"]["image-right"] = {"template_layout": "Two Content", "fields": {
        "title": {"idx": 0, "kind": "text", "max_chars": 70, "required": True},
        "body": {"idx": 1, "kind": "bullets", "max_chars": 60},
        "image": {"idx": 2, "kind": "image", "required": True}}}
    t["layouts"]["content"]["fields"]["body"]["max_bullet_chars"] = 200
    tokens.write_text(yaml.safe_dump(t))
    (ws / "decks" / "assets").mkdir()
    Image.new("RGB", (800, 600), "#556677").save(ws / "decks" / "assets" / "run.png")
    p = write_deck(ws, """
        ## Runs finish in four minutes
        layout: image-right

        ### image
        ![The run page](assets/run.png)

        ### body
        We start each run at six, and the retries cover the two sources that fail most often.
        """)
    code, out = cli_json(ws, "check", str(p), capsys=capsys)
    hit = _issues(out, "BUDGET_CHARS")[0]
    assert hit["field"] == "body"
    assert hit["message"].endswith("layouts that hold it as written: image (caption); content (body), which "
                                   "drops the image")


def test_a_title_over_budget_gets_no_layout_hint(ws, capsys):
    p = write_deck(ws, f"""
        ## {"A title that runs well past the seventy characters this layout's title holds"}
        layout: content

        - One point
        """)
    code, out = cli_json(ws, "check", str(p), capsys=capsys)
    hit = _issues(out, "BUDGET_CHARS")[0]
    assert hit["field"] == "title" and "layouts that hold" not in hit["message"]


def _built(ws: Path, capsys, body: str) -> Path:
    p = write_deck(ws, body)
    code, out = cli_json(ws, "build", str(p), capsys=capsys)
    assert code == 0, out
    return Path(out["output"])


def test_inspect_text_and_index_read_any_pptx(ws, capsys):
    out_pptx = _built(ws, capsys, """
        ## Orders ship the same day
        layout: content

        - Most orders ship from `orders.daily` by **four**
          - Late ones go out first the next morning

        Notes:
        Source: the March shipping log.

        ## Two warehouses share the load
        layout: two-col

        ### left
        - The main warehouse

        ### right
        - The overflow site
        """)
    prs = Presentation(str(out_pptx))
    p14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
    ext = etree.SubElement(etree.SubElement(prs.part._element, qn("p:extLst")), qn("p:ext"),
                           uri="{521415D9-36F7-43E2-AB2F-B90AF26B5E84}")
    sec = etree.SubElement(etree.SubElement(ext, f"{{{p14}}}sectionLst"), f"{{{p14}}}section", name="Shipping")
    etree.SubElement(etree.SubElement(sec, f"{{{p14}}}sldIdLst"), f"{{{p14}}}sldId", id=str(prs.slides[1].slide_id))
    edited = ws / "edited.pptx"
    prs.save(str(edited))

    code, out = cli_json(ws, "inspect", str(edited), "--text", capsys=capsys)
    assert code == 0
    first, second = out["slides"]
    assert first["title"] == "Orders ship the same day" and first["notes"] == "Source: the March shipping log."
    body = next(sh for sh in first["shapes"] if sh["kind"] == "text")
    assert body["lines"] == ["Most orders ship from `orders.daily` by **four**",
                             "  Late ones go out first the next morning"]
    assert second["section"] == "Shipping" and second["number"] == "2" and not second["hidden"]

    assert main(["inspect", str(edited), "--index"]) == 0
    index = capsys.readouterr().out.splitlines()
    assert index[1].split() == ["2", "number", "2", "Shipping", "|", "Two", "warehouses", "share", "the", "load"]
    assert main(["inspect", str(edited), "--text"]) == 0
    text = capsys.readouterr().out
    assert "--- slide 2: layout 'Two Content', number 2, section 'Shipping'" in text and "notes:" in text


def test_import_reads_any_common_monospace_font_as_code():
    assert importer.is_code_font("Consolas", "Menlo") and importer.is_code_font("Courier New", "Menlo")
    assert importer.is_code_font("Menlo", "Menlo") and not importer.is_code_font("Arial", "Menlo")
    assert not importer.is_code_font(None, "Menlo") and not importer.is_code_font("", "")


def test_check_and_build_say_why_slide_numbers_are_off(ws, capsys):
    p = write_deck(ws, """
        ---
        slide_numbers: false
        ---
        ## Orders ship the same day
        layout: content

        - Most orders ship by four
        """)
    code, out = cli_json(ws, "check", str(p), capsys=capsys)
    assert out["slide_numbers"] is False and "slide_numbers: false" in out["slide_numbers_off"]
    assert main(["--config", str(ws / "deck-builder.toml"), "build", str(p)]) == 0
    assert "slide numbers off: the front matter says slide_numbers: false" in capsys.readouterr().out
    p.write_text(p.read_text().replace("slide_numbers: false\n", ""))
    code, out = cli_json(ws, "check", str(p), capsys=capsys)
    assert out["slide_numbers"] is True and out["slide_numbers_off"] is None and "SLIDE_REF" not in codes(out)
