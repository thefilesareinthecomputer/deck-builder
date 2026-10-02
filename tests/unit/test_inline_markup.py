"""Inline markup in deck.md text: bold, italic, code spans and links, including nested markup."""
from pptx import Presentation

from deck_builder.build.text import CODE_FONT_DEFAULT, add_runs


def paragraph():
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(0, 0, 1, 1)
    return box.text_frame.paragraphs[0]


def runs(text):
    p = paragraph()
    add_runs(p, text)
    return [(r.text, bool(r.font.bold), bool(r.font.italic), r.font.name) for r in p.runs]


def test_plain_bold_is_unchanged():
    assert runs("**bold**") == [("bold", True, False, None)]


def test_bold_around_a_code_span_keeps_the_code_formatting_and_drops_no_backticks():
    assert runs("**`code`**") == [("code", True, False, CODE_FONT_DEFAULT)]


def test_italic_around_a_code_span_keeps_both_formats():
    assert runs("*`code`*") == [("code", False, True, CODE_FONT_DEFAULT)]


def test_bold_text_around_a_code_span_keeps_the_plain_part_bold_too():
    assert runs("**see `code` here**") == [
        ("see ", True, False, None),
        ("code", True, False, CODE_FONT_DEFAULT),
        (" here", True, False, None),
    ]


def test_a_code_span_with_literal_asterisks_inside_is_still_literal():
    assert runs("`a**b`") == [("a**b", False, False, CODE_FONT_DEFAULT)]
