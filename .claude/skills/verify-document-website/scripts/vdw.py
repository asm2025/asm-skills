#!/usr/bin/env python3
"""
vdw.py - verification harness for the document-website skill.

Run `setup` with the system Python. Run every other subcommand with the venv
Python that `setup` prints as PY=..., because they need Pillow and python-docx.

    python  vdw.py setup                      # prints PY=... and RUN=...
    "$PY"   vdw.py doctor  --run "$RUN"
    "$PY"   vdw.py fixture --out "$RUN/work/page.png"
    "$PY"   vdw.py run     --run "$RUN" --name annotate-all -- "$PY" skills/document-website/scripts/annotate.py ...
    "$PY"   vdw.py probe   --image out.png --at 320,150 --at 10,10
    "$PY"   vdw.py find    --image out.png --color 255,255,255 --region 300,130,340,170
    "$PY"   vdw.py diff    --before in.png --after out.png
    "$PY"   vdw.py docx-dump --docx out.docx --out "$RUN/evidence/doc.txt"
    "$PY"   vdw.py template --out "$RUN/work/acme.docx" [--dotx] [--no-heading2]
    "$PY"   vdw.py cleanup --run "$RUN" [--venv]
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DEFAULT = Path(tempfile.gettempdir()) / "verify-document-website"
REPO = Path(__file__).resolve().parents[4]
SCRIPTS = REPO / "skills" / "document-website" / "scripts"
DEPS = ["Pillow", "python-docx", "arabic-reshaper", "python-bidi"]


def venv_python(root: Path) -> Path:
    sub = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    return root / "venv" / sub


def posix(p: Path) -> str:
    return Path(p).resolve().as_posix()


# --------------------------------------------------------------------------- setup

def cmd_setup(a):
    root = Path(a.root)
    root.mkdir(parents=True, exist_ok=True)
    py = venv_python(root)
    if not py.exists():
        print(f"[setup] creating venv in {root / 'venv'}", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "venv", str(root / "venv")])
    print("[setup] ensuring deps: " + ", ".join(DEPS), file=sys.stderr)
    subprocess.check_call([str(py), "-m", "pip", "install", "-q",
                           "--disable-pip-version-check", *DEPS])
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{os.getpid()}"
    run = root / "runs" / stamp
    (run / "work").mkdir(parents=True)
    (run / "evidence").mkdir(parents=True)
    print(f"PY={posix(py)}")
    print(f"RUN={posix(run)}")
    # The Playwright MCP only writes inside the repo, so browser screenshots land in the
    # folder the skill's own screenshot_dir.py picks for this repo, in a per-run subfolder.
    print(f"SHOTS={posix(shots_dir(run))}")


def shots_dir(run: Path) -> Path:
    sys.dont_write_bytecode = True  # keep __pycache__ out of the repo
    sys.path.insert(0, str(SCRIPTS))
    import screenshot_dir
    base, _ = screenshot_dir.resolve(REPO)
    return base / f"vdw-{Path(run).name}"


# --------------------------------------------------------------------------- doctor

def cmd_doctor(a):
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("ok    " if cond else "FAIL  ") + msg)
        ok = ok and bool(cond)

    run = Path(a.run).resolve()
    check(run.is_dir() and (run / "evidence").is_dir(), f"run dir {posix(run)}")
    check(REPO not in run.parents, "run dir is outside the repo")
    for name in ("annotate.py", "build_docx.py"):
        check((SCRIPTS / name).is_file(), f"script {name}")
    try:
        head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "skills"],
                               capture_output=True, text=True).stdout.strip()
        print(f"info  repo {posix(REPO)} @ {head or '?'}"
              + (" (skills/ has uncommitted changes)" if dirty else ""))
    except FileNotFoundError:
        print("info  git not found; build revision unknown")
    print(f"info  python {sys.version.split()[0]} at {posix(Path(sys.executable))}, "
          f"utf8_mode={sys.flags.utf8_mode}")
    try:
        import PIL
        check(True, f"Pillow {PIL.__version__}")
    except ImportError:
        check(False, "Pillow importable (run doctor with the PY from setup)")
    try:
        import docx  # noqa: F401
        from importlib.metadata import version
        check(True, f"python-docx {version('python-docx')}")
    except ImportError:
        check(False, "python-docx importable (run doctor with the PY from setup)")
    if ok:
        sys.dont_write_bytecode = True  # keep __pycache__ out of the repo
        sys.path.insert(0, str(SCRIPTS))
        import annotate
        from PIL import features
        for sample in ("Click here", "✓", "完成"):
            _, path, missing = annotate.pick_font(sample, 16)
            print(f"info  annotate.py font for {sample!r}: {path}"
                  + (f" (missing {' '.join(missing)})" if missing else ""))
        try:
            import arabic_reshaper  # noqa: F401
            import bidi  # noqa: F401
            rtl = "arabic-reshaper + python-bidi"
        except ImportError:
            rtl = "none"
        print(f"info  right-to-left shaping: raqm={features.check('raqm')}, fallback={rtl}")
    sys.exit(0 if ok else 1)


# --------------------------------------------------------------------------- fixture

def cmd_fixture(a):
    from PIL import Image, ImageDraw
    w, h = (int(v) for v in a.size.lower().split("x"))
    if a.kind == "contrast":
        # Four full-height strips, a quarter of the width each.
        colors = [(232, 131, 58), (0, 0, 0), (255, 255, 255), (119, 119, 119)]
        img = Image.new("RGB", (w, h))
        d = ImageDraw.Draw(img)
        for i, col in enumerate(colors):
            d.rectangle([w * i // 4, 0, w * (i + 1) // 4 - 1, h - 1], fill=col)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        img.save(a.out)
        print(f"fixture {posix(Path(a.out))} {w}x{h}: four strips, orange (232,131,58), "
              f"black (0,0,0), white (255,255,255), gray (119,119,119), each {w // 4} px wide")
        return
    img = Image.new("RGB", (w, h), (245, 246, 248))            # page background
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 64], fill=(33, 47, 61))               # header bar
    d.rectangle([w - 220, 16, w - 40, 48], fill=(25, 118, 210))  # header button
    d.rectangle([200, 300, 600, 344], fill=(255, 255, 255), outline=(180, 180, 180))  # form field
    d.rectangle([200, 380, 360, 424], fill=(25, 118, 210))       # submit button
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(a.out)
    print(f"fixture {posix(Path(a.out))} {w}x{h}: bg (245,246,248), header (33,47,61) y0-64, "
          f"header button (25,118,210) [{w-220},16,{w-40},48], field [200,300,600,344], "
          f"submit (25,118,210) [200,380,360,424]")


# --------------------------------------------------------------------------- run

class WindowsLock:
    """Hold a file open with no sharing, the way Word holds an open document."""

    def __init__(self, path):
        self.path, self.handle = str(path), None

    def __enter__(self):
        if os.name != "nt":
            sys.exit("run --lock: Word-style file locks exist only on Windows")
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateFileW.restype = wintypes.HANDLE
        k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                    wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        GENERIC_RW, OPEN_EXISTING = 0xC0000000, 3
        h = k32.CreateFileW(self.path, GENERIC_RW, 0, None, OPEN_EXISTING, 0, None)
        if h in (None, wintypes.HANDLE(-1).value):
            sys.exit(f"run --lock: cannot open {self.path} (error {ctypes.get_last_error()})")
        self.k32, self.handle = k32, h
        return self

    def __exit__(self, *exc):
        self.k32.CloseHandle(self.handle)


def cmd_run(a):
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        sys.exit("run: give the command after --")
    if a.lock:
        with WindowsLock(a.lock):
            p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
    else:
        p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    ev = Path(a.run) / "evidence" / f"{a.name}.txt"
    locked = f"(held {posix(Path(a.lock))} open with no sharing)\n" if a.lock else ""
    record = (f"$ {subprocess.list2cmdline(cmd)}\n(cwd {posix(REPO)})\n{locked}"
              f"exit: {p.returncode}\n--- stdout\n{p.stdout}--- stderr\n{p.stderr}")
    ev.write_text(record, encoding="utf-8")
    print(record + f"(saved {posix(ev)})")
    sys.exit(p.returncode)


# --------------------------------------------------------------------------- probe / diff

def cmd_probe(a):
    from PIL import Image
    img = Image.open(a.image).convert("RGB")
    print(f"{posix(Path(a.image))} size {img.size[0]}x{img.size[1]}")
    for pt in a.at:
        x, y = (int(v) for v in pt.split(","))
        inside = 0 <= x < img.size[0] and 0 <= y < img.size[1]
        print(f"({x},{y}) {img.getpixel((x, y)) if inside else 'outside the image'}")


def cmd_find(a):
    from PIL import Image
    img = Image.open(a.image).convert("RGB")
    want = tuple(int(v) for v in a.color.split(","))
    x0, y0, x1, y1 = (int(v) for v in a.region.split(",")) if a.region else (0, 0, *img.size)
    x0, y0 = max(0, x0), max(0, y0)  # clamp the region to the image
    x1, y1 = min(img.size[0], x1), min(img.size[1], y1)
    xs, ys = [], []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if all(abs(c - w) <= a.tolerance for c, w in zip(img.getpixel((x, y)), want)):
                xs.append(x)
                ys.append(y)
    if not xs:
        print(f"color {want} not found in [{x0},{y0},{x1},{y1})")
        sys.exit(1)
    bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
    print(f"color {want} +/-{a.tolerance}: {len(xs)} pixels, bbox [{bx0},{by0},{bx1},{by1}], "
          f"center ({(bx0 + bx1) / 2:.1f},{(by0 + by1) / 2:.1f})")


def cmd_diff(a):
    from PIL import Image, ImageChops
    before = Image.open(a.before).convert("RGB")
    after = Image.open(a.after).convert("RGB")
    if before.size != after.size:
        print(f"SIZE MISMATCH before {before.size} after {after.size}")
        sys.exit(1)
    delta = ImageChops.difference(before, after).convert("L").point(lambda v: 255 if v else 0)
    bbox = delta.getbbox()
    changed = delta.histogram()[255]
    print(f"size {before.size[0]}x{before.size[1]}, changed pixels {changed}, "
          f"changed bbox {list(bbox) if bbox else None}")
    if a.region:
        x0, y0, x1, y1 = (int(v) for v in a.region.split(","))
        sub = delta.crop((x0, y0, x1, y1)).histogram()[255]
        print(f"changed pixels inside region [{x0},{y0},{x1},{y1}): {sub}")


# --------------------------------------------------------------------------- docx-dump

def cmd_docx_dump(a):
    from docx import Document
    from docx.shared import Emu
    doc = Document(a.docx)
    lines = [f"docx {posix(Path(a.docx))}"]
    for i, p in enumerate(doc.paragraphs):
        blips = p._p.xpath(".//pic:pic")
        align = p.alignment if p.alignment is not None else "-"
        tag = f"[{i:02d}] style={p.style.name!r} align={align}"
        if blips:
            for shape in blips:
                ext = shape.xpath(".//a:ext")
                cx = Emu(int(ext[0].get("cx"))).inches if ext else 0
                tag += f" IMAGE width={cx:.2f}in"
        runs = [r for r in p.runs if r.text]
        fmt = ""
        if runs:
            r = runs[0]
            fmt = (f" italic={r.font.italic} size={r.font.size.pt if r.font.size else None}"
                   f" color={r.font.color.rgb if r.font.color and r.font.color.type else None}")
        lines.append(f"{tag}{fmt} text={p.text!r}")
    lines.append(f"inline images: {len(doc.inline_shapes)}")
    normal = doc.styles["Normal"].font.size
    lines.append(f"Normal style font size: {normal.pt if normal else None}")
    sec = doc.sections[0]
    lines.append(f"section: page {sec.page_width.inches:.2f}x{sec.page_height.inches:.2f}in margins "
                 f"{sec.left_margin.inches:.2f}/{sec.right_margin.inches:.2f}/"
                 f"{sec.top_margin.inches:.2f}/{sec.bottom_margin.inches:.2f}in")
    lines.append("header: " + repr(" | ".join(p.text for p in sec.header.paragraphs if p.text)))
    lines.append("footer: " + repr(" | ".join(p.text for p in sec.footer.paragraphs if p.text)))
    lines.append(f"tables: {len(doc.tables)}")
    for name in ("Normal", "Title", "Heading 2", "Caption"):
        try:
            st = doc.styles[name]
        except KeyError:
            lines.append(f"style {name}: missing")
            continue
        size = st.font.size.pt if st.font.size else None
        color = st.font.color.rgb if st.font.color and st.font.color.type else None
        align = st.paragraph_format.alignment
        lines.append(f"style {name}: font={st.font.name} size={size} color={color} "
                     f"bold={st.font.bold} italic={st.font.italic} "
                     f"align={align if align is not None else '-'}")
    out = "\n".join(lines)
    print(out)
    if a.out:
        Path(a.out).write_text(out + "\n", encoding="utf-8")
        print(f"(saved {posix(Path(a.out))})")


# --------------------------------------------------------------------------- template

DOCX_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
DOTX_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"


def cmd_template(a):
    import zipfile
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Inches(0.5)
    sec.header.paragraphs[0].text = "ACME Header"
    sec.footer.paragraphs[0].text = "ACME Footer"
    doc.add_paragraph("TEMPLATE BODY TEXT")
    doc.add_table(rows=2, cols=2)
    h2 = doc.styles["Heading 2"]
    h2.font.name = "Georgia"
    h2.font.color.rgb = RGBColor.from_string("0B3D91")
    doc.styles["Title"].font.color.rgb = RGBColor.from_string("8B0000")
    cap = doc.styles["Caption"]
    cap.font.italic = True
    cap.font.size = Pt(8)
    cap.font.color.rgb = RGBColor.from_string("008000")
    if a.no_heading2:
        el = doc.styles["Heading 2"].element
        el.getparent().remove(el)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    if a.dotx:
        src = out.read_bytes()
        tmp = out.with_name(out.name + ".tmp")
        with zipfile.ZipFile(out) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "[Content_Types].xml":
                    data = data.replace(DOCX_MAIN.encode(), DOTX_MAIN.encode())
                zout.writestr(item, data)
        tmp.replace(out)
        assert out.read_bytes() != src
    print(f"template {posix(out)}: Letter, margins 0.5 in, header/footer ACME, 2x2 table, "
          f"{'.dotx content type, ' if a.dotx else ''}{'no Heading 2 style' if a.no_heading2 else 'Heading 2 Georgia 0B3D91'}")


# --------------------------------------------------------------------------- cleanup

def cmd_cleanup(a):
    root = Path(a.root).resolve()
    run = Path(a.run).resolve()
    if root not in run.parents:
        sys.exit(f"cleanup: refusing {posix(run)}; not under {posix(root)}")
    work = run / "work"
    if work.exists():
        shutil.rmtree(work)
        print(f"removed {posix(work)}")
    ev = run / "evidence"
    kept = sorted(p.name for p in ev.iterdir()) if ev.exists() else []
    shots = shots_dir(run)
    if shots.exists():
        shutil.rmtree(shots)
        print(f"removed {posix(shots)}")
    if shots.parent.is_dir() and not any(shots.parent.iterdir()):
        shots.parent.rmdir()  # the screenshots folder only held this run's subfolder
    print(f"kept evidence {posix(ev)}: {', '.join(kept) or '(empty)'}")
    if a.venv and (root / "venv").exists():
        shutil.rmtree(root / "venv")
        print(f"removed {posix(root / 'venv')}")


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Verification harness for skills/document-website.")
    ap.add_argument("--root", default=str(ROOT_DEFAULT),
                    help=f"harness root holding venv/ and runs/ (default {posix(ROOT_DEFAULT)})")
    sp = ap.add_subparsers(dest="cmd", required=True)

    sp.add_parser("setup", help="create/refresh the venv and a new run dir").set_defaults(fn=cmd_setup)

    p = sp.add_parser("doctor", help="read-only health check")
    p.add_argument("--run", required=True)
    p.set_defaults(fn=cmd_doctor)

    p = sp.add_parser("fixture", help="write a synthetic 'web page' PNG with known colors")
    p.add_argument("--out", required=True)
    p.add_argument("--size", default="1280x720")
    p.add_argument("--kind", choices=["form", "contrast"], default="form",
                   help="form: the page with buttons (default); contrast: four color strips")
    p.set_defaults(fn=cmd_fixture)

    p = sp.add_parser("run", help="run a command from the repo root and record it as evidence")
    p.add_argument("--run", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--lock", help="Windows only: hold this file open with no sharing while the command runs")
    p.add_argument("cmd", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_run)

    p = sp.add_parser("probe", help="print RGB at points")
    p.add_argument("--image", required=True)
    p.add_argument("--at", action="append", required=True, help="x,y (repeatable)")
    p.set_defaults(fn=cmd_probe)

    p = sp.add_parser("find", help="bbox and center of pixels matching a color")
    p.add_argument("--image", required=True)
    p.add_argument("--color", required=True, help="r,g,b")
    p.add_argument("--region", help="x0,y0,x1,y1: search only this box")
    p.add_argument("--tolerance", type=int, default=0, help="max per-channel difference")
    p.set_defaults(fn=cmd_find)

    p = sp.add_parser("diff", help="count and bound changed pixels between two PNGs")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--region", help="x0,y0,x1,y1: also count changes inside this box")
    p.set_defaults(fn=cmd_diff)

    p = sp.add_parser("docx-dump", help="list paragraphs, styles, images, run formatting")
    p.add_argument("--docx", required=True)
    p.add_argument("--out")
    p.set_defaults(fn=cmd_docx_dump)

    p = sp.add_parser("template", help="write a Word template with a known header, footer, margins, and styles")
    p.add_argument("--out", required=True)
    p.add_argument("--dotx", action="store_true", help="use the .dotx (template) content type")
    p.add_argument("--no-heading2", action="store_true", help="delete the Heading 2 style")
    p.set_defaults(fn=cmd_template)

    p = sp.add_parser("cleanup", help="delete the run's work/ (keeps evidence/)")
    p.add_argument("--run", required=True)
    p.add_argument("--venv", action="store_true", help="also delete the shared venv")
    p.set_defaults(fn=cmd_cleanup)

    a = ap.parse_args()
    try:
        a.fn(a)
    except FileNotFoundError as e:
        sys.exit(f"[vdw] file not found: {e.filename or e}")
    except Exception as e:  # e.g. python-docx PackageNotFoundError, PIL UnidentifiedImageError
        if type(e).__name__ in ("PackageNotFoundError", "UnidentifiedImageError"):
            sys.exit(f"[vdw] {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
