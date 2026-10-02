"""Make a saved PPTX byte-stable, and stamp deck-builder's custom properties.

python-pptx records the current time in zip entry headers and in the chart workbooks it embeds
(checked against python-pptx 1.0.2). Every zip entry, outer and nested, is rewritten with a fixed
timestamp and fixed attributes, and the embedded workbooks' own dates are fixed.
"""
from __future__ import annotations

import hashlib
import io
import re
import zipfile
from xml.sax.saxutils import escape

FIXED_TIME = (1980, 1, 1, 0, 0, 0)
W3C_DATE = re.compile(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*(</dcterms:(?:created|modified)>)")
CUSTOM_PART = "docProps/custom.xml"
CUSTOM_CT = "application/vnd.openxmlformats-officedocument.custom-properties+xml"
CUSTOM_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"


def _entry(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 0
    info.external_attr = 0
    return info


def _rezip(parts: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in parts:
            z.writestr(_entry(name), data)
    return buf.getvalue()


def _read(blob: bytes) -> list[tuple[str, bytes]]:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return [(i.filename, z.read(i.filename)) for i in z.infolist()]


def _fix_dates(xml: bytes, date: str) -> bytes:
    return W3C_DATE.sub(lambda m: m.group(1) + date.encode() + m.group(2), xml)


def _embedded_workbook(blob: bytes, date: str) -> bytes:
    parts = [(n, _fix_dates(d, date) if n == "docProps/core.xml" else d) for n, d in _read(blob)]
    return _rezip(parts)


def _custom_xml(props: dict[str, str]) -> bytes:
    rows = "".join(
        f'<property fmtid="{FMTID}" pid="{pid}" name="{escape(k)}"><vt:lpwstr>{escape(v)}</vt:lpwstr></property>'
        for pid, (k, v) in enumerate(sorted(props.items()), start=2)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        f"{rows}</Properties>"
    ).encode()


def _add_custom(parts: list[tuple[str, bytes]], props: dict[str, str]) -> list[tuple[str, bytes]]:
    out = []
    for name, data in parts:
        if name == "[Content_Types].xml" and CUSTOM_CT.encode() not in data:
            data = data.replace(
                b"</Types>", f'<Override PartName="/{CUSTOM_PART}" ContentType="{CUSTOM_CT}"/></Types>'.encode()
            )
        elif name == "_rels/.rels" and CUSTOM_REL.encode() not in data:
            data = data.replace(
                b"</Relationships>",
                f'<Relationship Id="rIdDeckBuilderCustom" Type="{CUSTOM_REL}" Target="{CUSTOM_PART}"/>'
                "</Relationships>".encode(),
            )
        if name != CUSTOM_PART:
            out.append((name, data))
    out.append((CUSTOM_PART, _custom_xml(props)))
    return out


def normalize(blob: bytes, date: str, props: dict[str, str]) -> bytes:
    """date is a W3C timestamp, e.g. 2000-01-01T00:00:00Z."""
    parts = []
    for name, data in _read(blob):
        if name.startswith("ppt/embeddings/") and name.endswith(".xlsx"):
            data = _embedded_workbook(data, date)
        elif name == "docProps/core.xml":
            data = _fix_dates(data, date)
        parts.append((name, data))
    return _rezip(_add_custom(parts, props))


def content_digest(blob: bytes) -> str:
    """A hash of every part's uncompressed bytes, stable across zlib versions and platforms."""
    h = hashlib.sha256()
    for name, data in sorted(_read(blob)):
        if name.startswith("ppt/embeddings/") and name.endswith(".xlsx"):
            data = content_digest(data).encode()
        h.update(name.encode() + b"\0" + hashlib.sha256(data).digest())
    return h.hexdigest()
