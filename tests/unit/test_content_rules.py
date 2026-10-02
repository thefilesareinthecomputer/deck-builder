"""Deck content the parser and validator reject with a message that says what to do."""
from conftest import cli_json, codes, write_deck


def test_a_stray_heading_in_a_slide_is_a_parse_error(ws, capsys):
    deck = write_deck(ws, """
        ## Volume grew
        layout: content

        - Copy paper led
        ### Some words with spaces
        - Card stock held flat
    """)
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert code == 1
    parse = [i for i in out["issues"] if i["code"] == "PARSE"]
    assert len(parse) == 1
    assert "'### Some words with spaces' isn't a slide or a field" in parse[0]["message"]
    assert parse[0]["line"] == 1


def test_a_top_level_heading_inside_a_slide_is_a_parse_error(ws, capsys):
    deck = write_deck(ws, "## Volume grew\nlayout: content\n\n# Stray\n- Copy paper led\n")
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert code == 1
    assert "PARSE" in codes(out)


def test_a_comment_inside_a_fenced_block_isnt_a_heading(ws, capsys):
    deck = write_deck(ws, """
        ## Volume by product
        layout: chart

        ```chart
        # cases shipped, thousands
        type: column
        categories: [Jul, Aug, Sep]
        series:
          - name: Copy paper
            values: [410, 378, 331]
        ```
    """)
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert code == 0, out["issues"]


def test_a_web_image_says_to_download_it(ws, capsys):
    deck = write_deck(ws, """
        ## Logo
        layout: image

        ![Logo](https://example.com/logo.png)
    """)
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    assert code == 1
    issue = next(i for i in out["issues"] if i["code"] == "MISSING_IMAGE")
    assert "'https://example.com/logo.png' is a web address" in issue["message"]
    assert "download it into the deck folder" in issue["message"]
