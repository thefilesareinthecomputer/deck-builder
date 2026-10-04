"""Untrusted decks and data rows can't write outside the workspace or pull in files from elsewhere."""
import json
from pathlib import Path

import pytest
from PIL import Image
from test_check import GOOD

from conftest import cli_json, codes, write_deck
from deck_builder.errors import EnvError
from deck_builder.qa import backends
from deck_builder.qa import render as qa_render

IMAGE_DECK = """
## Photo
layout: image

![A photo]({ref})
"""


def png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (800, 600), "#336699").save(path)
    return path


def with_output(output: str) -> str:
    return GOOD.replace("brand: stock\n", f"brand: stock\noutput: {output}\n")


# ---------------------------------------------------------------- where builds write


@pytest.mark.parametrize("output", ["../escape.pptx", "/tmp/escape.pptx", "../out/deck.txt"])
def test_front_matter_output_outside_the_deck_folder_or_out_is_refused(ws, capsys, output):
    code, out = cli_json(ws, "build", str(write_deck(ws, with_output(output))), capsys=capsys)
    assert code == 2
    assert f"front matter output: {output!r} must be a .pptx inside the deck's folder" in out["error"]
    assert not (ws / "escape.pptx").exists()


@pytest.mark.parametrize("output, where", [("../out/named.pptx", "out/named.pptx"), ("here.pptx", "decks/here.pptx")])
def test_front_matter_output_inside_the_deck_folder_or_out_builds(ws, capsys, output, where):
    code, out = cli_json(ws, "build", str(write_deck(ws, with_output(output))), capsys=capsys)
    assert code == 0, out["issues"]
    assert Path(out["output"]).resolve() == (ws / where).resolve()


def test_an_existing_file_without_a_manifest_is_never_replaced(ws, capsys):
    deck = write_deck(ws, GOOD)
    (ws / "out").mkdir()
    precious = ws / "out" / "decks.pptx"
    precious.write_bytes(b"someone's hand-edited deck")
    code, out = cli_json(ws, "build", str(deck), capsys=capsys)
    assert code == 2
    assert "has no decks.manifest.json beside it" in out["error"]
    assert precious.read_bytes() == b"someone's hand-edited deck"


def test_a_previous_build_is_replaced(ws, capsys):
    deck = write_deck(ws, GOOD)
    assert cli_json(ws, "build", str(deck), capsys=capsys)[0] == 0
    code, out = cli_json(ws, "build", str(deck), capsys=capsys)
    assert code == 0, out["issues"]


def test_a_hand_edited_build_output_is_never_replaced(ws, capsys):
    deck = write_deck(ws, GOOD)
    code, out = cli_json(ws, "build", str(deck), capsys=capsys)
    assert code == 0, out["issues"]
    pptx = Path(out["output"])
    before = pptx.read_bytes()
    pptx.write_bytes(before + b"hand-edited bytes appended after the build")
    code, out = cli_json(ws, "build", str(deck), capsys=capsys)
    assert code == 2
    assert "pass --force" in out["error"] or "--force" in out["error"]
    assert pptx.read_bytes() == before + b"hand-edited bytes appended after the build"


def test_force_replaces_a_hand_edited_build_output(ws, capsys):
    deck = write_deck(ws, GOOD)
    code, out = cli_json(ws, "build", str(deck), capsys=capsys)
    assert code == 0, out["issues"]
    pptx = Path(out["output"])
    pptx.write_bytes(pptx.read_bytes() + b"hand-edited bytes")
    code, out = cli_json(ws, "build", str(deck), "--force", capsys=capsys)
    assert code == 0, out["issues"]


def test_build_writes_no_leftover_tmp_files(ws, capsys):
    deck = write_deck(ws, GOOD)
    code, out = cli_json(ws, "build", str(deck), capsys=capsys)
    assert code == 0, out["issues"]
    leftovers = list((ws / "out").glob("*.tmp"))
    assert leftovers == []


def test_output_flag_needs_a_pptx_or_an_existing_folder(ws, capsys):
    code, out = cli_json(ws, "build", str(write_deck(ws, GOOD)), "-o", str(ws / "newname"), capsys=capsys)
    assert code == 2
    assert "-o takes a .pptx path or an existing folder" in out["error"]
    assert not (ws / "newname").exists()


# ---------------------------------------------------------------- what decks read


def test_an_image_in_the_deck_folder_is_recorded_by_its_source(ws, capsys):
    png(ws / "decks" / "assets" / "photo.png")
    code, out = cli_json(ws, "build", str(write_deck(ws, IMAGE_DECK.format(ref="assets/photo.png"))), capsys=capsys)
    assert code == 0, out["issues"]
    manifest = json.loads(Path(out["manifest"]).read_text())
    asset = manifest["slides"][0]["fields"]["image"]["asset"]
    assert (asset["ref"], asset["source"]) == ("assets/photo.png", "assets/photo.png")


def test_a_brand_logo_is_recorded_relative_to_the_kit(ws, capsys):
    code, out = cli_json(ws, "build", str(write_deck(ws, IMAGE_DECK.format(ref="brand:logo/primary"))),
                         capsys=capsys)
    assert code == 0, out["issues"]
    asset = json.loads(Path(out["manifest"]).read_text())["slides"][0]["fields"]["image"]["asset"]
    assert asset["source"] == "assets/logo.png"


@pytest.mark.parametrize("make_ref", [
    lambda ws: str(png(ws / "private" / "secret.png")),  # absolute
    lambda ws: (png(ws / "private" / "secret.png"), "../private/secret.png")[1],  # ..
])
def test_an_image_outside_the_deck_folder_is_an_error(ws, capsys, make_ref):
    ref = make_ref(ws)
    code, out = cli_json(ws, "check", str(write_deck(ws, IMAGE_DECK.format(ref=ref))), capsys=capsys)
    assert code == 1
    issue = next(i for i in out["issues"] if i["code"] == "ASSET_OUTSIDE")
    assert issue["message"].startswith(f"{ref!r} is outside the deck's folder")


def test_a_symlink_out_of_the_deck_folder_is_an_error(ws, capsys):
    secret = png(ws / "private" / "secret.png")
    (ws / "decks" / "assets").mkdir()
    (ws / "decks" / "assets" / "innocent.png").symlink_to(secret)
    deck = write_deck(ws, IMAGE_DECK.format(ref="assets/innocent.png"))
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert code == 1
    assert "ASSET_OUTSIDE" in codes(out)
    assert str(ws / "private") not in json.dumps(out)  # the message names the ref, not where it points


def test_an_outside_path_that_doesnt_exist_says_outside_not_missing(ws, capsys):
    deck = write_deck(ws, IMAGE_DECK.format(ref="../../../nope.png"))
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert codes(out) == ["ASSET_OUTSIDE"]  # no hint about whether the file exists


def test_a_missing_image_message_names_the_ref_not_the_resolved_path(ws, capsys):
    code, out = cli_json(ws, "check", str(write_deck(ws, IMAGE_DECK.format(ref="assets/nope.png"))), capsys=capsys)
    issue = next(i for i in out["issues"] if i["code"] == "MISSING_IMAGE")
    assert str(ws) not in issue["message"]


@pytest.mark.parametrize("ref", [
    "brand:icon/../../../../private/secret",  # icons/ -> assets/ -> stock/ -> brands/ -> ws/private/secret.png
    "brand:icon/a\\b", "brand:logo/../primary", "brand:logo/a/b",
])
def test_brand_ids_that_could_name_a_path_are_unknown(ws, capsys, ref):
    png(ws / "private" / "secret.png")
    deck = write_deck(ws, f"## Checked\nlayout: icon\nicon: {ref}\n" if "icon" in ref
                      else IMAGE_DECK.format(ref=ref))
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert code == 1
    assert "UNKNOWN_ASSET" in codes(out)


def test_an_explicit_template_outside_the_deck_folder_is_refused(ws, capsys):
    kit = "../brands/stock"
    body = GOOD.replace("brand: stock\n", f"template: {kit}/template.pptx\ntokens: {kit}/tokens.yaml\n")
    code, out = cli_json(ws, "check", str(write_deck(ws, body)), capsys=capsys)
    assert code == 2
    assert "must be files inside the deck's folder" in out["error"]


# ---------------------------------------------------------------- bulk data rows


def bulk(ws, capsys, body, rows):
    deck = write_deck(ws, body)
    data = ws / "rows.csv"
    data.write_text(rows, encoding="utf-8")
    return cli_json(ws, "build", str(deck), "--data", str(data), "--name", "{{_row}}.pptx", capsys=capsys)


BULK = "---\nbrand: stock\n---\n\n## {{client}} review\nlayout: content\n\n{{note}}\n"


def test_a_line_break_in_a_data_value_is_refused(ws, capsys):
    code, out = bulk(ws, capsys, BULK, 'client,note\nAcme,"fine"\nGlobex,"one\n## Injected slide"\n')
    assert code == 1
    issue = next(i for i in out["issues"] if i["code"] == "BAD_DATA_VALUE")
    assert issue["message"] == "row 2: column 'note' holds a line break"
    assert len(out["outputs"]) == 1  # row 1 still builds


@pytest.mark.parametrize("sep", ["\x0b", "\x0c", "\x1c", "\x85", "\N{LINE SEPARATOR}", "\N{PARAGRAPH SEPARATOR}"])
def test_any_line_separator_in_a_data_value_is_refused(ws, capsys, sep):
    code, out = bulk(ws, capsys, BULK, f'client,note\nAcme,"ok{sep}# Injected"\n')
    assert code == 1
    assert out["issues"][0]["message"] == "row 1: column 'note' holds a line break"


@pytest.mark.parametrize("value", ["# Injected heading", "![x](/etc/secret.png)"])
def test_a_value_that_would_start_a_heading_or_image_line_is_refused(ws, capsys, value):
    code, out = bulk(ws, capsys, BULK, f'client,note\nAcme,"{value}"\n')
    assert code == 1
    assert "row 1: column 'note' would start a heading or image line" in out["issues"][0]["message"]


@pytest.mark.parametrize("value", ["layout: title", "title: x", "| a | b |"])
def test_a_value_that_would_start_a_field_line_or_table_row_is_refused(ws, capsys, value):
    code, out = bulk(ws, capsys, BULK, f'client,note\nAcme,"{value}"\n')
    assert code == 1
    assert "row 1: column 'note' would start a heading or image line" in out["issues"][0]["message"]


def test_a_field_line_injected_with_no_blank_line_cant_override_the_layout(ws, capsys):
    # the template puts the data value immediately after `layout:`, with no blank line between them, so a
    # value that looks like another field line would otherwise be read as one by the head-of-slide scan
    tmpl = "---\nbrand: stock\n---\n\n## {{client}} review\nlayout: content\n{{note}}\n"
    code, out = bulk(ws, capsys, tmpl, 'client,note\nAcme,"layout: title"\n')
    assert code == 1
    assert "BAD_DATA_VALUE" in codes(out)
    assert not out.get("outputs")


def test_an_empty_value_cant_move_the_next_one_to_the_line_start(ws, capsys):
    body = "---\nbrand: stock\n---\n\n## {{client}} review\nlayout: content\n\n{{pad}}{{note}}\n"
    code, out = bulk(ws, capsys, body, 'client,pad,note\nAcme,,"![x](assets/a.png)"\n')
    assert code == 1
    assert "column 'pad', 'note' would start a heading or image line" in out["issues"][0]["message"]


@pytest.mark.parametrize("value", ["Notes:", "```chart"])
def test_a_value_that_would_start_notes_or_a_fence_is_refused(ws, capsys, value):
    code, out = bulk(ws, capsys, BULK, f'client,note\nAcme,"{value}"\n')
    assert code == 1 and "would start a heading or image line" in out["issues"][0]["message"]


def test_the_same_value_mid_line_is_plain_text(ws, capsys):
    code, out = bulk(ws, capsys, BULK, 'client,note\n# 1 supplier,ok\n')
    assert code == 0, out["issues"]


def test_an_image_ref_from_a_data_row_is_confined_per_row(ws, capsys):
    png(ws / "decks" / "assets" / "ok.png")
    png(ws / "private" / "secret.png")
    body = "---\nbrand: stock\n---\n\n## Photo\nlayout: image\n\n![A photo]({{img}})\n"
    code, out = bulk(ws, capsys, body, "img\nassets/ok.png\n../private/secret.png\n")
    assert code == 1
    errors = [i for i in out["issues"] if i["severity"] == "error"]
    assert [(i["code"], i["message"].split(":")[0]) for i in errors] == [("ASSET_OUTSIDE", "row 2")]
    assert len(out["outputs"]) == 1


# ---------------------------------------------------------------- render folder


def test_rendering_a_file_that_isnt_a_pptx_is_a_clear_error(tmp_path):
    pptx = tmp_path / "deck.pptx"
    pptx.write_text("not a pptx")
    with pytest.raises(EnvError, match="isn't a PowerPoint file"):
        qa_render.render(pptx, "libreoffice", 96, 20, None, None)


def test_rerendering_deletes_only_the_files_render_writes(tmp_path, monkeypatch):
    from pptx import Presentation

    pptx = tmp_path / "deck.pptx"
    Presentation().save(str(pptx))
    out_dir = tmp_path / "deck.render"
    out_dir.mkdir()
    for name in ("deck.pdf", "slide-01.png", "slide-12.png", "contact-01.png", "my-notes.md", "slide-01-edit.png"):
        (out_dir / name).write_text("x")

    def stop(*_a, **_k):
        raise EnvError("stop before rendering")

    monkeypatch.setattr(backends, "to_pdf", stop)
    with pytest.raises(EnvError):
        qa_render.render(pptx, "libreoffice", 96, 20, None, None)
    assert sorted(p.name for p in out_dir.iterdir()) == ["my-notes.md", "slide-01-edit.png"]
