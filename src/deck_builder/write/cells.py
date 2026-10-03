"""Model values as cell text, shared by the workbook and CSV writers."""
from __future__ import annotations

import re

from deck_builder.model import Bullets, Code, Image, Value


def bullets_text(items: Bullets) -> str:
    return "\n".join(f"{'  ' * lvl}- {text}" for lvl, text in items)


def _ranges(lines: list[int]) -> str:
    """[3, 5, 6, 7] -> "3,5-7"."""
    spans: list[list[int]] = []
    for n in lines:
        if spans and n == spans[-1][1] + 1:
            spans[-1][1] = n
        else:
            spans.append([n, n])
    return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in spans)


def code_md(c: Code) -> str:
    """A code block as a fenced block: backticks, one more than the longest backtick fence inside it, so a
    markdown example holding its own fence stays one block; tildes when the info string holds a backtick."""
    info = [c.language] if c.language else []
    if c.highlight:
        info.append("{" + _ranges(c.highlight) + "}")
    if c.numbers:
        info.append("lines")
    if c.title:
        info.append('title="' + c.title.replace("\\", "\\\\").replace('"', '\\"') + '"')
    line = " ".join(info)
    char = "~" if "`" in line else "`"
    runs = [len(m.group(0)) for ln in c.lines if (m := re.match(re.escape(char) + "{3,}", ln))]
    fence = char * max(3, max(runs, default=0) + 1)
    return f"{fence}{line}\n{c.text}\n{fence}"


def cell_text(value: Value) -> str:
    """Text, bullets, images and code as cell text. Charts and tables go to their own sheets."""
    if isinstance(value, list):
        return bullets_text(value)
    if isinstance(value, Image):
        return f"![{value.alt}]({value.ref})"
    if isinstance(value, Code):
        return code_md(value)
    return str(value)
