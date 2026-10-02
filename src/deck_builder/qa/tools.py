"""Find the external tools rendering needs. Nothing here installs anything."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

MAC_SOFFICE = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
POWERPOINT_APP = Path("/Applications/Microsoft PowerPoint.app")
POPPLER = ("pdftoppm", "pdftotext", "pdffonts")

INSTALL = {
    "poppler": {"darwin": "brew install poppler", "linux": "sudo apt-get install poppler-utils"},
    "libreoffice": {"darwin": "brew install --cask libreoffice", "linux": "sudo apt-get install libreoffice-impress"},
}


def soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    return str(MAC_SOFFICE) if MAC_SOFFICE.exists() else None


def poppler_missing() -> list[str]:
    return [t for t in POPPLER if shutil.which(t) is None]


def powerpoint() -> bool:
    return sys.platform == "darwin" and POWERPOINT_APP.exists()


def install_hint(tool: str) -> str:
    return INSTALL[tool].get("darwin" if sys.platform == "darwin" else "linux", "")
