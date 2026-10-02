"""PPTX -> PDF through PowerPoint for Mac (exact) or LibreOffice (close). Same output either way."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from deck_builder.errors import EnvError
from deck_builder.qa import tools

PP_CONTAINER = Path("~/Library/Containers/com.microsoft.Powerpoint/Data/deck-builder").expanduser()
PP_TIMEOUT = 180
LO_TIMEOUT = 300

# Open by path, save as PDF, close only that presentation. Quitting is decided by the caller.
APPLESCRIPT = """
on run argv
    set deckPath to item 1 of argv
    set pdfPath to item 2 of argv
    tell application "Microsoft PowerPoint"
        open (POSIX file deckPath)
        set pres to active presentation
        save pres in ((POSIX file pdfPath) as text) as save as PDF
        close pres saving no
    end tell
end run
"""


def choose(requested: str) -> str:
    if requested == "powerpoint":
        if not tools.powerpoint():
            raise EnvError("PowerPoint for Mac isn't installed; use --backend libreoffice")
        return "powerpoint"
    if requested == "libreoffice":
        if tools.soffice() is None:
            raise EnvError(f"LibreOffice not found; install it: {tools.install_hint('libreoffice')}")
        return "libreoffice"
    if tools.powerpoint():
        return "powerpoint"
    if tools.soffice() is not None:
        return "libreoffice"
    raise EnvError("no renderer: install Microsoft PowerPoint (Mac) or LibreOffice "
                   f"({tools.install_hint('libreoffice')})")


def libreoffice(pptx: Path, pdf: Path) -> None:
    exe = tools.soffice()
    if exe is None:
        raise EnvError("LibreOffice not found")
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp, "profile").as_uri()  # throwaway profile: never touches the user's LibreOffice
        cmd = [exe, f"-env:UserInstallation={profile}", "--headless", "--norestore", "--convert-to", "pdf",
               "--outdir", tmp, str(pptx.resolve())]  # absolute, so a name can't read as an option
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=LO_TIMEOUT)
        except subprocess.TimeoutExpired as e:
            raise EnvError(f"LibreOffice took longer than {LO_TIMEOUT}s; nothing was rendered") from e
        out = Path(tmp, pptx.stem + ".pdf")
        if not out.is_file():
            raise EnvError(f"LibreOffice didn't produce a PDF: {proc.stderr.strip() or proc.stdout.strip()}")
        shutil.copyfile(out, pdf)


def _running() -> bool:
    proc = subprocess.run(["osascript", "-e", 'application "Microsoft PowerPoint" is running'],
                          capture_output=True, text=True, timeout=20)
    return proc.stdout.strip() == "true"


def powerpoint(pptx: Path, pdf: Path) -> None:
    """Unverified on a real Mac until scripts/probe_powerpoint.sh passes; callers flag the result."""
    PP_CONTAINER.mkdir(parents=True, exist_ok=True)
    lock = PP_CONTAINER / ".lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as e:
        if time.time() - lock.stat().st_mtime < PP_TIMEOUT * 2:
            raise EnvError(f"another render is using PowerPoint (lock {lock}); try again shortly") from e
        lock.unlink()  # stale lock from a crashed run
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    try:
        was_running = _running()
        stem = f"render-{os.getpid()}"
        src, out = PP_CONTAINER / f"{stem}.pptx", PP_CONTAINER / f"{stem}.pdf"
        shutil.copyfile(pptx, src)
        try:
            proc = subprocess.run(["osascript", "-", str(src), str(out)], input=APPLESCRIPT, capture_output=True,
                                  text=True, timeout=PP_TIMEOUT)
        except subprocess.TimeoutExpired as e:
            raise EnvError(f"PowerPoint took longer than {PP_TIMEOUT}s (a dialog may be open); it was left "
                           "running", code="OFFICE_REPAIR") from e
        if "-1743" in proc.stderr:
            raise EnvError("macOS denied automation of PowerPoint. Allow it in System Settings > Privacy & "
                           "Security > Automation for the app running this command, then retry")
        if proc.returncode != 0 or not out.is_file():
            raise EnvError(f"PowerPoint didn't produce a PDF: {proc.stderr.strip()}", code="OFFICE_REPAIR")
        shutil.copyfile(out, pdf)
        for p in (src, out):
            p.unlink(missing_ok=True)
        if not was_running:
            subprocess.run(["osascript", "-e", 'tell application "Microsoft PowerPoint" to quit'],
                           capture_output=True, timeout=30)
    finally:
        lock.unlink(missing_ok=True)


def to_pdf(backend: str, pptx: Path, pdf: Path) -> None:
    (powerpoint if backend == "powerpoint" else libreoffice)(pptx, pdf)
