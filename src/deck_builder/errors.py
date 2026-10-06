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
    "AMBIGUOUS_DECK": (
        "A folder passed as the deck holds more than one of deck.md, deck.xlsx and deck.csv.",
        "Pass the deck file itself, or remove the extra copy from the folder.",
    ),
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
        "Remove one path from brand_paths, or ask the user which kit keeps the slug; `deck-builder brand copy "
        "<slug> <new-slug>` keeps the other under a new name.",
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
        "A slide uses a layout name the brand doesn't define. A generated kit can lack a layout this "
        "deck-builder has: one added since the kit was generated, or one outside its generate.layout_set.",
        "Use a layout from `deck-builder brand show <slug>`. For a layout the message says the kit can get, ask "
        "the brand owner before regenerating the kit with `deck-builder brand init <slug> --force`.",
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
        "Move the text to a layout with room for it (the message names the ones that hold it as written), split "
        "the slide, or move detail to speaker notes. Cut words only where each sentence stays whole. Never raise "
        "the budget to pass.",
    ),
    "BUDGET_BULLETS": (
        "A bullets field has more bullets than its budget.",
        "Merge or cut bullets, or split the slide.",
    ),
    "BUDGET_BULLET_CHARS": (
        "A single bullet is longer than the per-bullet budget.",
        "Split it into two bullets that are each a whole sentence, move detail to the notes, or move the text to "
        "a layout with room for it (the message names the ones that hold it as written).",
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
    "BUDGET_LINES": (
        "A text field, wrapped at its box's line length, needs more lines than the box holds. A list counts each "
        "bullet's own lines and the space before it, so short lines that make every bullet wrap show here even "
        "under the character budget. Inline `code` counts at the code font's width, which is wider.",
        "Move the text to a layout with room for it (the message names the ones that hold it as written), use "
        "fewer bullets, or move detail to the notes. Shorten a bullet only where it stays a whole sentence.",
    ),
    "CODE_LONG": (
        "A code block has a line longer than its panel is wide, or more lines than the panel holds (a `title=` "
        "filename line takes two). Code never wraps, so the line would run off the panel. As a warning: an "
        "inline `code` span longer than a line of its text field, which breaks mid-token.",
        "Break the long line where the language allows, shorten names, cut lines that don't make the point, "
        "or split the code across two slides. Keep an inline span short, or move it to a code block.",
    ),
    "CODE_LANGUAGE": (
        "A code block's language tag isn't one the highlighter knows, so the block builds as plain text.",
        "Use the language's usual name or short alias (python, sql, yaml, bash, json, ts); `text` is plain on "
        "purpose.",
    ),
    "CODE_LINES_MANY": (
        "A code block on a projected slide has more than 12 lines, more than an audience reads during one "
        "slide. A convention from `docs design`, so it warns.",
        "Cut to the lines that make the point and mark them with `{3,5-7}`, or move the full listing to the "
        "notes or an appendix.",
    ),
    "PROSE_TELL": (
        "Slide text has a countable writing tell: a dash, curly quote, ellipsis or arrow character, an emoji, an "
        "inflated word (leverage, seamless, robust), an intensifier standing in for a number (significantly, "
        "dramatically), a filler transition (moreover, that said), a teaser (here's the catch), or a third "
        "\"X, not Y\" contrast in the deck. Speaker notes, code and quoted words are left alone.",
        "Use the plain word or the number, cut the filler, state the point instead of teasing it, and type the "
        "plain character. `docs voice` has the writing rules.",
    ),
    "SLIDE_REF": (
        "Slide text or speaker notes name another slide by its position: \"slide 12\", \"the previous slide\", "
        "\"the next slide\". Slides get reordered, and pasted into other decks, so the reference goes stale.",
        "Name what that slide shows instead (\"the cost table\", \"the rollout timeline\").",
    ),
    "INVISIBLE_CHAR": (
        "Slide text or speaker notes hold a character a reader can't see (a no-break space, a zero-width or "
        "direction mark) or a private-use glyph, which shows as an empty box outside the font that made it. "
        "They break search and text comparison. PowerPoint makes some itself, such as a symbol-font smiley from "
        "\":)\".",
        "Run `deck-builder fix-text <deck file>`: it turns no-break spaces into spaces, deletes the rest and lists "
        "each change. An agent with no shell reports the warning to the main agent, which runs it.",
    ),
    "BULLETS_MANY": (
        "A list on a projected slide has more than four bullets, past what an audience holds at once. "
        "A convention from `docs design`, so it warns.",
        "Cut to the four that make the point, split the slide, or move detail to the speaker notes.",
    ),
    "WORDS_MANY": (
        "A projected slide has more than 60 words; about 40 reads well from the back of a room. "
        "A convention from `docs design`, so it warns.",
        "Move detail to the speaker notes, or split the slide.",
    ),
    "LAYOUT_RUN": (
        "More than three slides in a row use the same layout, so the deck reads as a document. "
        "A convention from `docs design`, so it warns.",
        "Match each point to the layout that shows it (`docs design` has the table): a number as big-number, "
        "parallel options as cards or comparison, steps as process.",
    ),
    "SERIES_MANY": (
        "A chart has more than eight series, more than its colors keep apart.",
        "Group the small series into one, or split the chart.",
    ),
    "MISSING_ALT": (
        "An image has no alt text, so a screen reader has nothing to say for it (WCAG 2.2 SC 1.1.1).",
        "Write what the image shows between the brackets: `![The new north warehouse](assets/hero.png)`.",
    ),
    "TITLE_DUPLICATE": (
        "Two slides have the same title; a screen reader lists slides by title, and PowerPoint's accessibility "
        "checker flags it (WCAG 2.2 SC 2.4.6).",
        "Give each slide a title that says what that slide shows.",
    ),
    "COLOR_ONLY": (
        "A chart's series or slices are told apart by color alone, which people with color blindness can't "
        "do (WCAG 2.2 SC 1.4.1).",
        "Leave the legend on (the default for two or more series and for pies) or set `labels: true`.",
    ),
    "CVD_CONFUSABLE": (
        "Two of the brand's chart colors look alike: the same color, or alike to people with a common color "
        "blindness (protanopia, deuteranopia or tritanopia), simulated on the colors themselves.",
        "Ask the brand owner to change one of the two colors in tokens.yaml `chart.colors` or the theme "
        "accents; until then, label the series on charts that use both.",
    ),
    "TYPE_SMALL": (
        "A size in `generate.type` is under the legibility floor for its mode: 18 pt for a projected deck, "
        "12 pt for a read deck.",
        "Raise the size in brand.yaml `generate.type` and regenerate the kit with `brand init <slug> --force`.",
    ),
    "TYPE_LARGE": (
        "A size in `generate.type` is taller than the box it goes in: the field holds less than one line, so "
        "its text always overflows.",
        "Set that `generate.type` size to the one the message says fits, then `brand init <slug> --force`.",
    ),
    "IMAGE_TEXT_CONTRAST": (
        "An image-full slide's white title, on its see-through band, measures under 4.5:1 against the lightest "
        "part of the photo under the band (WCAG 2.2 SC 1.4.3).",
        "Choose a photo, or a crop of it, that's darker where the band sits; or use the image or image-right "
        "layout, which keep text off the photo.",
    ),
    "IMAGE_NO_SLOT": (
        "A slide's speaker notes name an image (a line starting `SCREENSHOT:` or `DIAGRAM:`) that its layout "
        "has no slot for, so the image shows only in the notes. Only the image layouts (image, image-right, "
        "image-2) hold one.",
        "Move the slide to a layout the message lists; it says what each costs in cuts. Or split the slide, or "
        "keep the image in the notes on purpose.",
    ),
    "IMAGE_CROPPED": (
        "An image is cropped to fill its box, and the crop takes more than lint.max_crop percent (default 15) of "
        "its height, from the top and bottom: where a screenshot has its title and last line.",
        "Add `fit: contain` to the slide to show the whole image, or `fit: cover` to keep the crop; or use an "
        "image closer to the box's shape.",
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
        "The target format can't hold everything in the input, such as charts or code blocks in CSV.",
        "Convert to .xlsx or .md instead.",
    ),
    "IMPORT_LOSSY": (
        "The deck.md import wrote doesn't reparse to the same slides it extracted from the .pptx: some "
        "content, often in speaker notes, collided with deck.md's own syntax.",
        "Open the named slide in deck.md, reword the colliding line, then run `deck-builder check`.",
    ),
    "KIT_STALE": (
        "A generated kit no longer matches what made it: brand.yaml's palette, fonts or generate settings, or "
        "the logo on the master, changed after `brand init`, or a different deck-builder generated it. The kit "
        "still builds as it is.",
        "Upgrading is the brand owner's call. `deck-builder brand init <slug> --force` rebuilds the kit from its "
        "own brand.yaml and assets, replacing tuned budgets and template edits, after copying the whole kit as "
        "it was into its backups/ folder, from which either can be copied back.",
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
