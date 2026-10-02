"""Checks and summaries for a whole brand kit: `brand check` and `brand show`."""
from __future__ import annotations

from typing import Any

from deck_builder import template as tpl
from deck_builder.brand import inspect as brand_inspect
from deck_builder.brand.registry import Brand
from deck_builder.errors import Issue


def color_refs(brand: Brand) -> list[tuple[str, str]]:
    """Every (where, ref) pair that must resolve to a palette name or hex."""
    refs: list[tuple[str, str]] = []
    for slot, ref in (brand.meta.get("theme_colors") or {}).items():
        refs.append((f"brand.yaml theme_colors.{slot}", str(ref)))
    icons = brand.meta.get("icons") or {}
    if icons.get("default_color"):
        refs.append(("brand.yaml icons.default_color", str(icons["default_color"])))
    for section in ("chart", "table"):
        for k, v in (brand.tokens.get(section) or {}).items():
            if k == "colors":
                refs += [(f"tokens.yaml {section}.colors", str(c)) for c in v]
            elif k == "status":
                refs += [(f"tokens.yaml {section}.status.{sk}", str(sv)) for sk, sv in v.items()]
            elif k.endswith(("_color", "_fill", "_text")) or k == "text":
                refs.append((f"tokens.yaml {section}.{k}", str(v)))
    for lname, ls in (brand.tokens.get("layouts") or {}).items():
        for fname, fs in (ls.get("fields") or {}).items():
            if fs.get("color"):
                refs.append((f"tokens.yaml layouts.{lname}.{fname}.color", str(fs["color"])))
    return refs


def luminance(hexv: str) -> float:
    """WCAG 2.2 relative luminance of a 6-digit hex color."""
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(int(hexv[i:i + 2], 16)) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


# (foreground slot, background slot, minimum): text needs 4.5:1 (WCAG 1.4.3); the dark title, section and
# closing layouts put lt1 text on dk2.
TEXT_PAIRS = (("dk1", "lt1", 4.5), ("dk1", "lt2", 4.5), ("lt1", "dk2", 4.5), ("hlink", "lt1", 4.5))
GRAPHIC_MIN = 3.0  # icons and chart series against the background (WCAG 1.4.11)


def contrast_issues(brand: Brand) -> list[Issue]:
    """LOW_CONTRAST warnings from the template's theme colors, the colors icons and charts use, and
    each table status color against every fill it can sit on (its row, its band, and the background)."""
    assert brand.template is not None
    slots = brand_inspect.theme(brand.template)["colors"]
    pairs = [(f"{fg} on {bg}", slots.get(fg), slots.get(bg), lo) for fg, bg, lo in TEXT_PAIRS]
    icon_ref = (brand.meta.get("icons") or {}).get("default_color")
    chart_refs = (brand.tokens.get("chart") or {}).get("colors") or []
    graphics = [("icon color", icon_ref)] if icon_ref else []
    if chart_refs:
        graphics += [("chart color", ref) for ref in chart_refs]
    else:  # no token colors: charts take the theme accents in order
        graphics += [("chart color", f"accent{n}") for n in range(1, 7)]
    seen = set()
    for what, ref in graphics:
        hexv = slots.get(str(ref)) or brand.color(str(ref))
        if hexv and hexv not in seen:
            seen.add(hexv)
            pairs.append((f"{what} {ref} on lt1", hexv, slots.get("lt1"), GRAPHIC_MIN))
    table_tok = brand.tokens.get("table") or {}
    backgrounds = [("row_fill", table_tok.get("row_fill")), ("band_fill", table_tok.get("band_fill")),
                   ("background", "lt1")]
    for key, ref in (table_tok.get("status") or {}).items():
        hexv = slots.get(str(ref)) or brand.color(str(ref))
        if not hexv:
            continue
        for bg_name, bg_ref in backgrounds:
            bg_hex = (slots.get(str(bg_ref)) or brand.color(str(bg_ref))) if bg_ref else None
            if bg_hex:
                pairs.append((f"table status {key} on {bg_name}", hexv, bg_hex, GRAPHIC_MIN))
    out = []
    for label, fg, bg, lo in pairs:
        if fg and bg and (ratio := contrast(fg, bg)) < lo:
            out.append(Issue("LOW_CONTRAST", f"{label} (#{fg} on #{bg}) is {ratio:.2f}:1; needs {lo}:1",
                             severity="warning", actual=round(ratio, 2), limit=lo))
    return out


def check_kit(brand: Brand) -> list[Issue]:
    out = [Issue("BRAND_INVALID", p) for p in brand.problems]
    out += [Issue("SCHEMA", e) for e in brand.schema_errors]
    if out:
        return out
    assert brand.template is not None
    prs_layouts = tpl.layouts(tpl.open_template(brand.template))
    for lname, ls in (brand.tokens.get("layouts") or {}).items():
        layout = tpl.find_layout(prs_layouts, ls["template_layout"], ls.get("master"))
        if layout is None:
            out.append(Issue("TEMPLATE_MISMATCH",
                             f"layout {lname!r}: template has no layout {ls['template_layout']!r}"))
            continue
        idxs = {ph.placeholder_format.idx for ph in layout.placeholders}
        for fname, fs in ls["fields"].items():
            if fs["idx"] not in idxs:
                out.append(Issue("TEMPLATE_MISMATCH",
                                 f"layout {lname!r} field {fname!r}: no placeholder idx {fs['idx']} on "
                                 f"{ls['template_layout']!r} (has {sorted(idxs)})", field=fname))
        hf = ls.get("heading_field")
        if hf and hf not in ls["fields"]:
            out.append(Issue("SCHEMA", f"layout {lname!r}: heading_field {hf!r} isn't one of its fields"))
    for where, ref in color_refs(brand):
        if brand.color(ref) is None:
            out.append(Issue("UNKNOWN_ASSET", f"{where}: {ref!r} is neither a palette name nor hex"))
    for lid, rel in (brand.meta.get("logos") or {}).items():
        if not (brand.path / rel).is_file():
            out.append(Issue("MISSING_IMAGE", f"logo {lid!r}: {rel} not found"))
    icons = brand.meta.get("icons") or {}
    if icons and not (brand.path / icons["dir"]).is_dir():
        out.append(Issue("MISSING_IMAGE", f"icons dir {icons['dir']} not found"))
    return out + contrast_issues(brand)


def _field_summary(fs: dict[str, Any]) -> str:
    s = fs.get("kind", "text")
    if fs.get("max_chars"):
        s += f"<={fs['max_chars']}"
    if fs.get("max_bullets"):
        s += f" x{fs['max_bullets']}"
        if fs.get("max_bullet_chars"):
            s += f"<={fs['max_bullet_chars']}"
    if fs.get("max_rows"):
        s += f" {fs['max_rows']}r x {fs.get('max_cols', '?')}c"
    if fs.get("required"):
        s += " *"
    return s


def show(brand: Brand) -> dict[str, Any]:
    """The compact contract an agent needs before writing a deck."""
    icons = brand.meta.get("icons") or {}
    icon_ids: list[str] = []
    if icons.get("dir") and (brand.path / icons["dir"]).is_dir():
        icon_ids = sorted(p.stem for p in (brand.path / icons["dir"]).glob("*.png"))
    layouts = {}
    for lname, ls in (brand.tokens.get("layouts") or {}).items():
        entry: dict[str, Any] = {"fields": {f: _field_summary(fs) for f, fs in ls["fields"].items()}}
        if ls.get("heading_field", "title") != "title":
            entry["heading"] = ls["heading_field"]
        if ls.get("description"):
            entry["use"] = ls["description"]
        layouts[lname] = entry
    return {
        "slug": brand.slug,
        "name": brand.name,
        "version": brand.version,
        "layouts": layouts,
        "palette": sorted((brand.meta.get("palette") or {}).keys()),
        "logos": sorted((brand.meta.get("logos") or {}).keys()),
        "icons": icon_ids,
        "voice": brand.meta.get("voice") or [],
        "lint": brand.meta.get("lint") or {},
    }


def show_text(d: dict[str, Any]) -> str:
    lines = [f"{d['slug']} {d['version']} - {d['name']}",
             "layouts (field kind<=chars, x bullets, * required):"]
    for lname, ls in d["layouts"].items():
        head = f" (## heading -> {ls['heading']})" if "heading" in ls else ""
        fields = ", ".join(f"{f} {s}" for f, s in ls["fields"].items())
        lines.append(f"  {lname}{head}: {fields}")
        if "use" in ls:
            lines.append(f"    use: {ls['use']}")
    lines.append(f"palette: {', '.join(d['palette'])}")
    if d["logos"]:
        lines.append(f"logos: {', '.join('brand:logo/' + x for x in d['logos'])}")
    if d["icons"]:
        lines.append(f"icons: {', '.join('brand:icon/' + x for x in d['icons'])}")
    for v in d["voice"]:
        lines.append(f"voice: {v}")
    if d["lint"]:
        lines.append(f"lint: {d['lint']}")
    return "\n".join(lines)
