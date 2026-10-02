"""Charts, tables and pictures into placeholders. Colors and sizes come from tokens.yaml."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Pt

from deck_builder.brand.registry import Brand
from deck_builder.build.text import CODE_FONT_DEFAULT, add_runs
from deck_builder.model import Chart, Table

CHART_TYPES = {
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "stacked-column": XL_CHART_TYPE.COLUMN_STACKED,
    "bar": XL_CHART_TYPE.BAR_CLUSTERED,
    "stacked-bar": XL_CHART_TYPE.BAR_STACKED,
    "line": XL_CHART_TYPE.LINE_MARKERS,
    "pie": XL_CHART_TYPE.PIE,
    "doughnut": XL_CHART_TYPE.DOUGHNUT,
}
# Documented defaults, used only when tokens.yaml doesn't set the value.
CHART_DEFAULTS = {"font_size": 12, "gap_width": 80, "line_width": 2.25, "gridlines": True}
TABLE_DEFAULTS = {"font_size": 14, "header_font_size": 14, "row_height_factor": 2.2}


def _rgb(brand: Brand, ref: Any) -> RGBColor | None:
    hexv = brand.color(str(ref)) if ref is not None else None
    return RGBColor.from_string(hexv) if hexv else None


def _take_geometry(ph: Any) -> tuple[int, int, int, int]:
    geo = (ph.left, ph.top, ph.width, ph.height)
    ph._element.getparent().remove(ph._element)
    return geo


def fill_chart(slide: Any, ph: Any, spec: Chart, brand: Brand) -> None:
    ct = CHART_TYPES[spec.type]
    data = CategoryChartData(number_format=spec.number_format)
    data.categories = spec.categories
    for sr in spec.series:
        data.add_series(sr.name, sr.values)
    if hasattr(ph, "insert_chart"):
        chart = ph.insert_chart(ct, data).chart
    else:
        chart = slide.shapes.add_chart(ct, *_take_geometry(ph), data).chart

    tok = {**CHART_DEFAULTS, **(brand.tokens.get("chart") or {})}
    names = spec.colors or tok.get("colors") or []
    colors = [c for c in (_rgb(brand, n) for n in names) if c is not None]
    if tok.get("font"):
        chart.font.name = tok["font"]
    chart.font.size = Pt(tok["font_size"])
    text_color = _rgb(brand, tok.get("text_color"))
    if text_color:
        chart.font.color.rgb = text_color
    pie = spec.type in ("pie", "doughnut")
    plot = chart.plots[0]
    if colors:
        if pie:
            for i, pt in enumerate(plot.series[0].points):
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = colors[i % len(colors)]
        else:
            for i, s in enumerate(plot.series):
                c = colors[i % len(colors)]
                if spec.type == "line":
                    s.format.line.color.rgb = c
                    s.format.line.width = Pt(tok["line_width"])
                    s.marker.format.fill.solid()
                    s.marker.format.fill.fore_color.rgb = c
                else:
                    s.format.fill.solid()
                    s.format.fill.fore_color.rgb = c
    if not pie and hasattr(plot, "gap_width"):
        plot.gap_width = tok["gap_width"]
    legend = spec.legend if spec.legend is not None else (pie or len(spec.series) > 1)
    chart.has_legend = bool(legend)
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
    if spec.labels:
        plot.has_data_labels = True
        plot.data_labels.number_format = spec.number_format
        plot.data_labels.number_format_is_linked = False
    chart.has_title = bool(spec.title)
    if spec.title:
        chart.chart_title.text_frame.text = spec.title
    if not pie:
        axis = chart.value_axis
        axis.has_major_gridlines = bool(tok["gridlines"])
        grid = _rgb(brand, tok.get("gridline_color"))
        if grid and axis.has_major_gridlines:
            axis.major_gridlines.format.line.color.rgb = grid
        axis.format.line.fill.background()
        axis.tick_labels.number_format = spec.number_format
        axis.tick_labels.number_format_is_linked = False


def fill_table(slide: Any, ph: Any, spec: Table, brand: Brand) -> None:
    nrows, ncols = len(spec.rows) + 1, len(spec.header)
    if hasattr(ph, "insert_table"):
        frame = ph.insert_table(nrows, ncols)
    else:
        frame = slide.shapes.add_table(nrows, ncols, *_take_geometry(ph))
    table = frame.table
    tok = {**TABLE_DEFAULTS, **(brand.tokens.get("table") or {})}
    code_font = (brand.tokens.get("text") or {}).get("code_font", CODE_FONT_DEFAULT)
    row_h = Pt(tok.get("row_height", max(tok["font_size"], tok["header_font_size"]) * tok["row_height_factor"]))
    for r in range(nrows):
        table.rows[r].height = row_h
    frame.height = row_h * nrows
    header_text, body_text = _rgb(brand, tok.get("header_text")), _rgb(brand, tok.get("text"))
    fills = {"header": _rgb(brand, tok.get("header_fill")), "row": _rgb(brand, tok.get("row_fill")),
             "band": _rgb(brand, tok.get("band_fill"))}
    for r in range(nrows):
        for c in range(ncols):
            cell = table.cell(r, c)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.text = ""
            add_runs(cell.text_frame.paragraphs[0], spec.header[c] if r == 0 else spec.rows[r - 1][c], code_font)
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    if tok.get("font"):
                        run.font.name = tok["font"]
                    run.font.size = Pt(tok["header_font_size"] if r == 0 else tok["font_size"])
                    if r == 0:
                        run.font.bold = True
                    color = header_text if r == 0 else body_text
                    if color:
                        run.font.color.rgb = color
            fill = fills["header"] if r == 0 else (fills["band"] if r % 2 == 0 else fills["row"])
            if fill:
                cell.fill.solid()
                cell.fill.fore_color.rgb = fill


def fill_picture(slide: Any, ph: Any, path: Path, alt: str, crop: bool) -> tuple[int, int, int, int]:
    """Crop to fill (photos in picture placeholders) or fit inside (logos, icons, other placeholders).

    Returns the placeholder's geometry, used for the low-resolution check.
    """
    geo = (ph.left, ph.top, ph.width, ph.height)
    if crop and hasattr(ph, "insert_picture"):
        pic = ph.insert_picture(str(path))
    else:
        left, top, w, h = _take_geometry(ph)
        with PILImage.open(path) as im:
            iw, ih = im.size
        scale = min(w / iw, h / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        pic = slide.shapes.add_picture(str(path), left + (w - nw) // 2, top + (h - nh) // 2, nw, nh)
    if alt:
        pic._element.nvPicPr.cNvPr.set("descr", alt)
    return geo
