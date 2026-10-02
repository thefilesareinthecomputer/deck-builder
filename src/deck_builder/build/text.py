"""Text and bullets into placeholders, with the inline markup deck.md allows."""
from __future__ import annotations

import re
from typing import Any

from deck_builder.model import Value

INLINE = re.compile(r"\*\*(?P<b>.+?)\*\*|\*(?P<i>.+?)\*|`(?P<c>[^`]+)`|\[(?P<lt>[^\]]+)\]\((?P<lu>[^)]+)\)")
CODE_FONT_DEFAULT = "Courier New"  # documented default; tokens.yaml text.code_font overrides


def add_runs(paragraph: Any, text: str, code_font: str = CODE_FONT_DEFAULT) -> None:
    """**bold**, *italic*, `code` and [text](url). Everything else is literal."""
    pos = 0
    for m in INLINE.finditer(text):
        if m.start() > pos:
            paragraph.add_run().text = text[pos : m.start()]
        run = paragraph.add_run()
        if m.group("b") is not None:
            run.text = m.group("b")
            run.font.bold = True
        elif m.group("i") is not None:
            run.text = m.group("i")
            run.font.italic = True
        elif m.group("c") is not None:
            run.text = m.group("c")
            run.font.name = code_font
        else:
            run.text = m.group("lt")
            run.hyperlink.address = m.group("lu")
        pos = m.end()
    if pos < len(text):
        paragraph.add_run().text = text[pos:]


def fill_text(ph: Any, value: Value, code_font: str = CODE_FONT_DEFAULT) -> None:
    tf = ph.text_frame
    items: list[tuple[int, str]] = [(0, value)] if isinstance(value, str) else list(value)  # type: ignore[arg-type]
    tf.text = ""
    for n, (lvl, txt) in enumerate(items):
        p = tf.paragraphs[0] if n == 0 else tf.add_paragraph()
        p.level = lvl
        add_runs(p, str(txt), code_font)
