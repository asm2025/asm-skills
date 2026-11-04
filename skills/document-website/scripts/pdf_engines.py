#!/usr/bin/env python3
"""
pdf_engines.py - find and run the programs that turn a tutorial into a PDF.

build_docx.py builds a .docx (for Word or LibreOffice) or an .html (for Chrome or Edge) in a
temporary folder and calls one function here to convert it. No Python package is needed; each
engine is a program the user already has. Every function writes its PDF where it is told to
(inside the build's temp folder) and raises PdfEngineError when the engine fails.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ENGINES = ("word", "libreoffice", "chrome")

INSTALL_HINTS = {
    "word": "Microsoft Word (Windows only)",
    "libreoffice": "LibreOffice (https://www.libreoffice.org), with soffice on PATH or in its "
                   "default install folder",
    "chrome": "Google Chrome or Microsoft Edge",
}


class PdfEngineError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Finding engines
# ---------------------------------------------------------------------------

def _word_installed() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            return True
    except OSError:
        return False


def _libreoffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (r"C:\Program Files\LibreOffice\program\soffice.exe",
                      r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                      "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if Path(candidate).is_file():
            return candidate
    return None


def _chrome() -> str | None:
    candidates = []
    if sys.platform == "win32":
        bases = [os.environ.get(v) for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
        for rel in (r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe"):
            candidates += [Path(b) / rel for b in bases if b]
    elif sys.platform == "darwin":
        candidates += [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                       Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    for name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
        found = shutil.which(name)
        if found:
            return found
    return None


def find_engines() -> dict:
    """Map each engine name to what runs it ("COM" for Word, a program path), or None."""
    return {"word": "COM" if _word_installed() else None,
            "libreoffice": _libreoffice(),
            "chrome": _chrome()}


def searched() -> str:
    return "; ".join(f"{name}: {INSTALL_HINTS[name]}" for name in ENGINES)


def pick_engine(requested: str, found: dict, prefer_chrome: bool = False) -> str:
    """Return the engine to use. `auto` takes the first found in ENGINES order, Chrome first
    when prefer_chrome is set (only Chrome uses CSS). A named engine must be found."""
    if requested != "auto":
        if requested not in ENGINES:
            raise PdfEngineError(f"unknown PDF engine '{requested}' (choose auto, "
                                 f"{', '.join(ENGINES)})")
        if found.get(requested):
            return requested
        raise PdfEngineError(f"PDF engine '{requested}' was not found. Searched for {searched()}. "
                             "Install it, or choose another engine with --pdf-engine.")
    order = (("chrome",) + tuple(e for e in ENGINES if e != "chrome")) if prefer_chrome else ENGINES
    for name in order:
        if found.get(name):
            return name
    raise PdfEngineError("no PDF engine found. Searched for " + searched()
                         + ". Install one of them, or build a .docx, .md, or .html instead.")


# ---------------------------------------------------------------------------
# Running engines
# ---------------------------------------------------------------------------

def _tail(text: str, lines: int = 8) -> str:
    kept = [ln for ln in (text or "").strip().splitlines() if ln.strip()]
    return "\n".join(kept[-lines:])


WORD_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($env:DW_IN, $false, $true)
    $doc.ExportAsFixedFormat($env:DW_OUT, 17)
    $doc.Close(0)
} finally {
    if ($doc -ne $null) {
        try { $doc.Close(0) } catch {}
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
    }
    if ($word -ne $null) {
        try { $word.Quit() } catch {}
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    }
}
"""

LIST_WORD_SCRIPT = (
    "Get-CimInstance Win32_Process -Filter \"Name='WINWORD.EXE'\" | ForEach-Object { "
    "'{0}|{1}|{2}' -f $_.ProcessId, ([DateTimeOffset]$_.CreationDate).ToUnixTimeSeconds(), "
    "$_.CommandLine }")


def _kill_word_started_after(started: float) -> None:
    """End Word instances that automation started (/Automation) after `started` (epoch seconds)."""
    try:
        listing = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", LIST_WORD_SCRIPT],
            capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return
    for line in listing.splitlines():
        pid, _, rest = line.partition("|")
        created, _, cmdline = rest.partition("|")
        try:
            is_new = int(created) >= int(started) - 1
        except ValueError:
            continue
        if is_new and "/automation" in cmdline.lower():
            subprocess.run(["taskkill", "/F", "/PID", pid.strip()], capture_output=True)


def docx_to_pdf_word(docx: Path, pdf: Path, timeout: int = 180) -> None:
    env = dict(os.environ, DW_IN=str(Path(docx).resolve()), DW_OUT=str(Path(pdf).resolve()))
    started = time.time()
    proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-Command", WORD_SCRIPT],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace")
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        _kill_word_started_after(started)
        raise PdfEngineError(f"Word did not finish within {timeout} seconds and was stopped")
    if proc.returncode != 0:
        raise PdfEngineError("Word could not convert the document:\n" + _tail(err or out))
    if not Path(pdf).is_file():
        raise PdfEngineError("Word finished but wrote no PDF:\n" + _tail(err or out))


def docx_to_pdf_libreoffice(docx: Path, pdf: Path, program: str = None,
                            timeout: int = 180) -> None:
    exe = program or find_engines()["libreoffice"]
    if not exe:
        raise PdfEngineError("LibreOffice was not found")
    docx = Path(docx).resolve()
    work = Path(tempfile.mkdtemp(prefix="document-website-lo-"))
    try:
        outdir = work / "out"
        outdir.mkdir()
        cmd = [exe, "--headless", "--norestore",
               f"-env:UserInstallation={(work / 'profile').as_uri()}",
               "--convert-to", "pdf", "--outdir", str(outdir), str(docx)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            raise PdfEngineError(f"LibreOffice did not finish within {timeout} seconds and was stopped")
        result = outdir / (docx.stem + ".pdf")
        if proc.returncode != 0 or not result.is_file():
            raise PdfEngineError("LibreOffice could not convert the document:\n"
                                 + _tail(proc.stderr or proc.stdout))
        shutil.move(str(result), str(pdf))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def html_to_pdf_chrome(html: Path, pdf: Path, browser: str, timeout: int = 120) -> None:
    html = Path(html).resolve()
    pdf = Path(pdf).resolve()
    profile = Path(tempfile.mkdtemp(prefix="document-website-chrome-"))
    try:
        cmd = [browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
               f"--user-data-dir={profile}", f"--print-to-pdf={pdf}", html.as_uri()]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            raise PdfEngineError(f"{Path(browser).name} did not finish within {timeout} seconds "
                                 "and was stopped")
        except OSError as e:
            raise PdfEngineError(f"could not start {browser}: {e.strerror or e}")
        ok = False
        if pdf.is_file():
            with open(pdf, "rb") as f:
                ok = f.read(5) == b"%PDF-"
        if proc.returncode != 0 or not ok:
            raise PdfEngineError(f"{Path(browser).name} could not print the page:\n"
                                 + _tail(proc.stderr or proc.stdout))
    finally:
        shutil.rmtree(profile, ignore_errors=True)
