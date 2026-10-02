"""Issue codes, issues and the exit-code contract.

Every code the engine can raise is defined here with its cause and fix. `deck-builder explain`
and `deck-builder docs codes` print from this table, so the docs can't drift from the engine.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

EXIT_OK = 0
EXIT_ISSUES = 1
EXIT_ENV = 2

# code -> (cause, fix)
CODES: dict[str, tuple[str, str]] = {
    "PARSE": (
        "The input can't be parsed: bad YAML, an unclosed block, a malformed table, or no slides.",
        "Fix the syntax at the reported line; `deck-builder docs deck-md` shows the format.",
    ),
    "SPEC_VERSION": (
        "The input declares a spec_version newer than this engine supports.",
        "Upgrade deck-builder, or lower spec_version if the input doesn't use newer features.",
    ),
    "SCHEMA": (
        "brand.yaml, tokens.yaml or a manifest doesn't match its JSON Schema.",
        "Fix the listed keys; `deck-builder schema brand` or `deck-builder schema tokens` prints the schema.",
    ),
    "UNKNOWN_BRAND": (
        "The deck names a brand slug that no brand_paths entry contains.",
        "Run `deck-builder brand list` and use a listed slug, or add the kit's folder to brand_paths.",
    ),
    "BRAND_DUPLICATE": (
        "Two brand kits under brand_paths use the same slug.",
        "Rename one kit's slug in its brand.yaml and folder, or remove one path from brand_paths.",
    ),
    "BRAND_INVALID": (
        "A brand kit is missing a required file or fails `brand check`.",
        "Run `deck-builder brand check <slug>` and fix what it lists.",
    ),
    "TEMPLATE_MISMATCH": (
        "tokens.yaml names a template layout or placeholder idx the template doesn't have.",
        "Run `deck-builder inspect <template>` and correct template_layout or idx in tokens.yaml.",
    ),
    "UNKNOWN_LAYOUT": (
        "A slide uses a layout name the brand doesn't define.",
        "Use a layout from `deck-builder brand show <slug>`.",
    ),
    "UNKNOWN_FIELD": (
        "A slide sets a field its layout doesn't have.",
        "Use the layout's field names from `brand show`, or switch to a layout that has the field.",
    ),
    "MISSING_FIELD": (
        "A required field for the slide's layout is empty.",
        "Fill the field, or choose a layout where it isn't required.",
    ),
    "KIND_MISMATCH": (
        "A field got the wrong kind of value, such as a table in a text field.",
        "Give the field the kind `brand show` lists, or move the content to a field of that kind.",
    ),
    "BUDGET_CHARS": (
        "A field has more characters than its budget.",
        "Cut words, split the slide, or move detail to speaker notes. Never raise the budget to pass.",
    ),
    "BUDGET_BULLETS": (
        "A bullets field has more bullets than its budget.",
        "Merge or cut bullets, or split the slide.",
    ),
    "BUDGET_BULLET_CHARS": (
        "A single bullet is longer than the per-bullet budget.",
        "Shorten the bullet or split it into two.",
    ),
    "BUDGET_LEVEL": (
        "Bullets nest deeper than the field allows.",
        "Flatten the nesting.",
    ),
    "TABLE_SHAPE": (
        "A table has no header, too many rows or columns, or rows of different lengths.",
        "Fix the table so every row matches the header and fits the field's limits.",
    ),
    "TABLE_TALL": (
        "A table's estimated rendered height, from its row count and each row's wrapped line count, "
        "exceeds its layout placeholder's height.",
        "Shorten cell text, cut rows or columns, or choose a layout with a taller table placeholder.",
    ),
    "CHART_SHAPE": (
        "A chart has an unknown type, no categories or series, or a series of the wrong length.",
        "Give every series one value per category and use a supported chart type.",
    ),
    "UNKNOWN_ASSET": (
        "A brand:logo, brand:icon or palette name doesn't exist in the brand.",
        "Run `deck-builder assets <slug>` for the available ids.",
    ),
    "ASSET_FORMAT": (
        "An image is in a format PowerPoint placeholders can't take, such as SVG.",
        "Convert it to PNG or JPEG.",
    ),
    "ASSET_LOW_RES": (
        "An image is smaller than its placeholder at 150 DPI and will look soft.",
        "Use a larger source image.",
    ),
    "MISSING_IMAGE": (
        "An image path doesn't exist, or the image is a web address.",
        "Fix the path; paths resolve relative to the deck file. Download a web image into the deck folder first.",
    ),
    "ASSET_OUTSIDE": (
        "An image path resolves outside the deck's folder, or a brand asset outside its kit, through an absolute "
        "path, `..` or a symlink. A deck can't pull files from elsewhere on the machine into a deliverable.",
        "Copy the image into the deck's folder and use its path relative to the deck file.",
    ),
    "BANNED_PATTERN": (
        "Slide text or notes match one of the brand's banned patterns.",
        "Reword the text. The pattern list is in the brand's brand.yaml under lint.",
    ),
    "MAX_SLIDES": (
        "The deck has more slides than the brand allows.",
        "Cut or merge slides.",
    ),
    "UNKNOWN_TOKEN": (
        "A {{token}} in a bulk template has no matching data column.",
        "Fix the token name or add the column to the data file.",
    ),
    "BAD_DATA_VALUE": (
        "A bulk data cell holds a line break, or a value that would start a heading or image line where its "
        "{{token}} sits, which would change the deck's structure instead of filling in text.",
        "Keep each cell to one line of plain text; put headings and images in the template, not the data.",
    ),
    "CSV_NO_SHEETS": (
        "A CSV input references a chart or table sheet, which CSV can't hold.",
        "Use an .xlsx workbook, or remove the sheet: reference.",
    ),
    "CONVERT_LOSSY": (
        "The target format can't hold everything in the input, such as charts in CSV.",
        "Convert to .xlsx or .md instead.",
    ),
    "LOW_CONTRAST": (
        "Two brand colors that sit on each other don't meet WCAG 2.2 contrast: 4.5:1 for text (ink on "
        "background or surface, background on primary, links on background), 3:1 for icons and chart series.",
        "Darken or lighten one color of the pair in the brand's palette, then `brand init` again. Change brand "
        "colors only with the brand owner's say-so.",
    ),
    "OVERFLOW_MEASURED": (
        "Rendered text runs past its placeholder box.",
        "Cut text in that field or split the slide, then rebuild and render again.",
    ),
    "EMPTY_PLACEHOLDER": (
        "A rendered slide has a placeholder with no content.",
        "Fill the field or use a layout without it.",
    ),
    "MISSING_FONT": (
        "The renderer used another font than the brand's, or its fallback: the font isn't installed where the "
        "deck rendered.",
        "Install the brand fonts where decks render. Don't change content to fit a substitute font; a "
        "PowerPoint render shows the real fonts.",
    ),
    "OFFICE_REPAIR": (
        "PowerPoint couldn't open or export the built file, or stopped on a dialog such as a repair prompt.",
        "A repair prompt on an engine-built file is an engine defect; report it with the input and manifest.",
    ),
    "RENDER_UNVERIFIED": (
        "The PowerPoint render backend hasn't been verified on a real Mac yet.",
        "Treat the render as provisional; run scripts/probe_powerpoint.sh to verify the backend.",
    ),
    "STALE_BUILD": (
        "The deck source recorded in the .pptx's manifest was edited after the .pptx was built.",
        "Rebuild the deck before trusting this render.",
    ),
    "SKILL_CONFLICT": (
        "`skills install` found a file or folder where it would put a link, and left it alone.",
        "Remove or rename the existing skill or agent if this clone's version should replace it, then rerun.",
    ),
}


@dataclass
class Issue:
    code: str
    message: str
    severity: str = "error"
    file: str | None = None
    line: int | None = None
    slide: int | None = None
    field: str | None = None
    actual: Any = None
    limit: Any = None

    def __post_init__(self) -> None:
        if self.code not in CODES:
            raise ValueError(f"unknown issue code {self.code!r}")

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def human(self) -> str:
        where = self.file or ""
        if self.line is not None:
            where += f":{self.line}"
        parts = [self.severity, self.code]
        if where:
            parts.append(where)
        if self.slide is not None:
            parts.append(f"slide {self.slide}")
        head = " ".join(parts)
        if self.field:
            head += f" {self.field}"
        return f"{head}: {self.message}"


@dataclass
class Result:
    """What every command returns: printed as one summary line, or as one JSON object."""

    command: str
    ok: bool = True
    summary: str = ""
    issues: list[Issue] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    exit_code: int = EXIT_OK

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)
        if issue.severity == "error":
            self.ok = False
            self.exit_code = max(self.exit_code, EXIT_ISSUES)

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"ok": self.ok, "command": self.command}
        out.update(self.data)
        out["issues"] = [i.as_dict() for i in self.issues]
        return out


class EnvError(Exception):
    """A usage or environment problem: missing file, missing tool. Exit code 2."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code
