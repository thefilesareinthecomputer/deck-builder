"""Open .potx/.pptx templates and look up their layouts."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

from pptx import Presentation

from deck_builder.errors import EnvError

POTX_CT = b"application/vnd.openxmlformats-officedocument.presentationml.template.main+xml"
PPTX_CT = b"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
MAX_UNPACKED = 200 * 2**20  # a template that unpacks larger than this is refused (zip bombs)


def open_template(path: Path) -> Any:
    """Open a .pptx or .potx. python-pptx rejects the .potx content type, so it's patched in memory."""
    if not path.is_file():
        raise EnvError(f"template not found: {path}")
    try:
        with zipfile.ZipFile(path) as z:
            size = sum(i.file_size for i in z.infolist())
    except zipfile.BadZipFile as e:
        raise EnvError(f"{path} isn't a PowerPoint file") from e
    if size > MAX_UNPACKED:
        raise EnvError(f"{path} unpacks to {size // 2**20} MB; templates over {MAX_UNPACKED // 2**20} MB are refused")
    if path.suffix.lower() != ".potx":
        return Presentation(str(path))
    buf = io.BytesIO()
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(POTX_CT, PPTX_CT)
            zout.writestr(item, data)
    buf.seek(0)
    return Presentation(buf)


def layouts(prs: Any) -> dict[tuple[str | None, str], Any]:
    """(master name, layout name) -> layout, plus (None, layout name) for the first match."""
    out: dict[tuple[str | None, str], Any] = {}
    for master in prs.slide_masters:
        mname = master.name if hasattr(master, "name") else None
        for layout in master.slide_layouts:
            out.setdefault((mname, layout.name), layout)
            out.setdefault((None, layout.name), layout)
    return out


def find_layout(prs_layouts: dict[tuple[str | None, str], Any], name: str, master: str | None = None) -> Any:
    return prs_layouts.get((master, name))


def remove_all_slides(prs: Any) -> None:
    """Drop any sample slides shipped inside the template."""
    sld_id_lst = prs.slides._sldIdLst
    for sld_id in list(sld_id_lst):
        prs.part.drop_rel(sld_id.rId)
        sld_id_lst.remove(sld_id)
