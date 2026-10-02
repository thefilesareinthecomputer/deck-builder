"""Checks and summaries for a whole brand kit: `brand check` and `brand show`."""
from __future__ import annotations

from typing import Any

from deck_builder import template as tpl
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
            elif k.endswith(("_color", "_fill", "_text")) or k == "text":
                refs.append((f"tokens.yaml {section}.{k}", str(v)))
    for lname, ls in (brand.tokens.get("layouts") or {}).items():
        for fname, fs in (ls.get("fields") or {}).items():
            if fs.get("color"):
                refs.append((f"tokens.yaml layouts.{lname}.{fname}.color", str(fs["color"])))
    return refs


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
    return out


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
