"""PROSE_TELL: the countable writing tells in slide text, as warnings from check."""
from __future__ import annotations

import pytest

from conftest import cli_json, write_deck
from deck_builder.validate import prose_tells


@pytest.mark.parametrize("text,kind", [
    ("Volume grew — again", "symbol"),
    ("We’re on track", "symbol"),
    ("Sales are up \U0001F680", "emoji"),
    ("We leverage the new routes", "inflated word"),
    ("A seamless hand-off", "inflated word"),
    ("Costs fell significantly", "intensifier"),
    ("Moreover, the north grew", "filler transition"),
    ("That said, margin held", "filler transition"),
    ("Here's the catch: freight", "teaser"),
    ("It ships monthly, not weekly", "contrast"),
])
def test_each_kind_of_tell_is_found(text, kind):
    assert kind in prose_tells(text)


@pytest.mark.parametrize("text", [
    "Volume grew 12% in Q3",
    "Run `leverage --robust` first",  # inline code is someone else's words
    'The manager said "a seamless week" and meant it',  # so is a quotation
    "Unlocked doors, a utility room and a significant-other discount",  # not the words themselves
])
def test_plain_text_quotes_and_code_are_quiet(text):
    assert prose_tells(text) == {}


def test_check_warns_per_field_and_only_from_the_third_contrast(ws, capsys):
    deck = write_deck(ws, """
        ---
        brand: stock
        ---

        ## Deliveries leverage the new routes
        layout: content

        - Weekly, not monthly
        - Online, not by phone

        ## A third contrast tips it over
        layout: content

        - Mornings, not evenings

        Notes:
        Moreover, the notes are left alone, not linted.
        """)
    code, out = cli_json(ws, "check", str(deck), capsys=capsys)
    tells = [(i["slide"], i["field"], i["message"].split(" ")[0]) for i in out["issues"] if i["code"] == "PROSE_TELL"]
    assert code == 0  # warnings only
    assert tells == [(1, "title", "inflated"), (2, "body", "contrast")]
