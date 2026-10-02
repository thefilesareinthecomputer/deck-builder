"""Text and bullets into placeholders, with the inline markup deck.md allows."""
from __future__ import annotations

import re
from typing import Any

from deck_builder.model import Value

INLINE = re.compile(r"\*\*(?P<b>.+?)\*\*|\*(?P<i>.+?)\*|`(?P<c>[^`]+)`|\[(?P<lt>[^\]]+)\]\((?P<lu>[^)]+)\)")
CODE_FONT_DEFAULT = "Courier New"  # documented default; tokens.yaml text.code_font overrides


def _styled_run(paragraph: Any, text: str, bold: bool, italic: bool, code_font: str | None = None) -> None:
    run = paragraph.add_run()
    run.text = text
    if bold:
        run.font.bold = True
    if italic:
        run.font.italic = True
    if code_font:
        run.font.name = code_font


def add_runs(paragraph: Any, text: str, code_font: str = CODE_FONT_DEFAULT, bold: bool = False,
            italic: bool = False) -> None:
    """**bold**, *italic*, `code` and [text](url). Everything else is literal.

    `**` or `*` around a code span or link captures the inner markup as literal characters (the
    outer pattern is lazy but still swallows them), so that inner text is re-scanned on its own,
    carrying the outer bold or italic down onto whatever runs it produces.
    """
    pos = 0
    for m in INLINE.finditer(text):
        if m.start() > pos:
            _styled_run(paragraph, text[pos : m.start()], bold, italic)
        if m.group("b") is not None:
            add_runs(paragraph, m.group("b"), code_font, bold=True, italic=italic)
        elif m.group("i") is not None:
            add_runs(paragraph, m.group("i"), code_font, bold=bold, italic=True)
        elif m.group("c") is not None:
            _styled_run(paragraph, m.group("c"), bold, italic, code_font)
        else:
            run = paragraph.add_run()
            run.text = m.group("lt")
            run.hyperlink.address = m.group("lu")
            if bold:
                run.font.bold = True
            if italic:
                run.font.italic = True
        pos = m.end()
    if pos < len(text):
        _styled_run(paragraph, text[pos:], bold, italic)


def fill_text(ph: Any, value: Value, code_font: str = CODE_FONT_DEFAULT) -> None:
    tf = ph.text_frame
    items: list[tuple[int, str]] = [(0, value)] if isinstance(value, str) else list(value)  # type: ignore[arg-type]
    tf.text = ""
    for n, (lvl, txt) in enumerate(items):
        p = tf.paragraphs[0] if n == 0 else tf.add_paragraph()
        p.level = lvl
        add_runs(p, str(txt), code_font)
