"""Syntax highlighting for code blocks: Pygments lexes the code, and each token gets one of a few roles.

Roles, not Pygments' own token types, are what tokens.yaml colors and the build styles: a kit holds one
color per role, and comments are italic and keywords bold, so color is never the only signal. Only the
lexers bundled with Pygments are used, never a plugin another installed package registers, so a language
tag means the same thing on every machine and a build stays byte-identical.
"""
from __future__ import annotations

from functools import cache
from typing import Any

from pygments.lexers import get_all_lexers, get_lexer_by_name
from pygments.token import Comment, Generic, Keyword, Literal, Name, Number, Operator, String

from deck_builder.model import Code

ROLES = ("keyword", "string", "comment", "number", "function", "type", "operator", "plain")
BOLD, ITALIC = frozenset({"keyword"}), frozenset({"comment"})
PLAIN = frozenset({"", "text", "plain", "plaintext", "txt"})  # no highlighting, and no warning either

# First match wins, so a specific type comes before its parent (Keyword.Type before Keyword).
ROLE_OF: tuple[tuple[Any, str], ...] = (
    (Comment, "comment"),
    (Keyword.Type, "type"),
    (Keyword.Constant, "number"),  # True, None, NULL: values, like numbers
    (Keyword, "keyword"),
    (Operator.Word, "keyword"),  # and, or, not, in
    (Operator, "operator"),
    (Name.Builtin.Pseudo, "plain"),  # self, cls
    (Name.Function, "function"),
    (Name.Decorator, "function"),
    (Name.Builtin, "function"),
    (Name.Tag, "function"),  # YAML keys, HTML tags
    (Name.Class, "type"),
    (Name.Exception, "type"),
    (String, "string"),
    (Number, "number"),
    (Literal.Date, "number"),
    (Generic.Heading, "keyword"),  # markdown headings
    (Generic.Subheading, "keyword"),
)


@cache
def _aliases() -> frozenset[str]:
    return frozenset(a for _, aliases, _, _ in get_all_lexers(plugins=False) for a in aliases)


def known(language: str) -> bool:
    """A language tag Pygments can highlight, or one of the plain-text tags."""
    return language.lower() in PLAIN or language.lower() in _aliases()


def role_of(ttype: Any) -> str:
    return next((role for parent, role in ROLE_OF if ttype in parent), "plain")


def lines(code: Code) -> list[list[tuple[str, str]]]:
    """Each line of the block as (role, text) runs, neighboring runs of one role merged. An unknown
    language comes back as plain text, which check reports as CODE_LANGUAGE."""
    name = code.language.lower()
    pieces: list[tuple[str, str]] = [("plain", code.text)]
    if name not in PLAIN and name in _aliases():
        lexer = get_lexer_by_name(name, stripnl=False, ensurenl=False)
        lexed = [(role_of(t), str(v)) for t, v in lexer.get_tokens(code.text)]
        if "".join(v for _, v in lexed) == code.text:  # a lexer that rewrites its input isn't trusted
            pieces = lexed
    out: list[list[tuple[str, str]]] = [[]]
    for role, text in pieces:
        for k, part in enumerate(text.split("\n")):
            if k:
                out.append([])
            if not part:
                continue
            row = out[-1]
            if row and (row[-1][0] == role or not part.strip()):  # spaces join whatever run they follow
                row[-1] = (row[-1][0], row[-1][1] + part)
            else:
                row.append((role, part))
    return out
