#!/usr/bin/env python3
"""
build_docx.py - Assemble a step-by-step tutorial from a steps JSON file.

The output format follows the --output extension:
    .docx         Word document (needs python-docx)
    .md           Markdown, with the images copied into <name>_images/ beside it
    .html / .htm  one self-contained HTML file with the images embedded
    .pdf          PDF through Word (Windows), LibreOffice, or Chrome/Edge (--pdf-engine)

Usage:
    python3 build_docx.py \
        --title  "My App - Getting Started" \
        --steps  steps.json \
        --output tutorial.docx \
        [--template company.docx] [--style style.json] [--css extra.css] [--pdf-engine auto]

steps.json (UTF-8) is an array of steps:
[
  {
    "heading": "Step 1: Log in",                          <- optional; defaults to "Step <n>"
    "body":    "Open the login page.\n\nEnter your email.", <- optional; blank lines split paragraphs
    "image":   "./docs/screenshots/login_annotated.png",  <- optional; a path or a list of paths
    "caption": "Login screen"                             <- optional; shown under the image(s)
  },
  ...
]

--template (.docx or .dotx, for .docx output) builds inside a Word template: its body is
cleared, and its styles, page setup, headers, and footers carry over.

--style reads the "document" section of a style file (see references/style-file.md): fonts,
sizes, colors, and alignment for the Word styles Normal, Title, Heading 2, and Caption, and the
page setup (not with --template). For .html it becomes CSS. --css (.html output, and .pdf output
built with Chrome) adds a stylesheet after that. For a template, the style file wins for the keys
it names.

.pdf output: Word and LibreOffice convert a .docx built with the template and style file; Chrome
(or Edge) prints the HTML build, so --style and --css apply and --template does not. --pdf-engine
auto takes the first of Word, LibreOffice, Chrome found (Chrome first when --css is given without
--template). Only a .pdf output starts an engine.

A relative image path is looked up from the current directory first, then from
the folder that holds steps.json.

Exit codes: 0 saved, 1 saved but an image was missing or unreadable (each one is
replaced by a red "[Image not found: ...]" line and listed on stderr), or the
output could not be written, 2 invalid arguments or steps (nothing written).
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdf_engines  # noqa: E402  (used as a module so tests can replace find_engines)
from style_file import (StyleError, load_style, parse_color,  # noqa: E402
                        validate_document)

FIELDS = ("heading", "body", "image", "caption")
MAX_WIDTH_IN, MAX_HEIGHT_IN, SCREEN_DPI = 6.0, 8.0, 96
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}


class StepsError(ValueError):
    pass


@dataclass
class BuildOptions:
    template: Path | None = None   # --template path
    document: Any = None           # the opened template (python-docx Document), set by main()
    style: dict = field(default_factory=dict)  # the style file's "document" section
    css: str | None = None         # contents of --css
    pdf_engine: str = ""           # the engine main() picked for .pdf output
    pdf_program: str = ""          # what runs that engine (path, or "COM" for Word)


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

def load_steps(path: Path) -> list:
    """Read and validate steps.json. Returns steps with 'images' resolved to Paths or misses."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise StepsError(f"steps file not found: {path}")
    except json.JSONDecodeError as e:
        raise StepsError(f"{path} is not valid JSON: {e}")
    if not isinstance(raw, list):
        raise StepsError(f"{path} must contain a JSON array of steps, got {type(raw).__name__}")

    errors, steps = [], []
    for i, step in enumerate(raw, start=1):
        if not isinstance(step, dict):
            errors.append(f"step {i}: must be an object, got {json.dumps(step)}")
            continue
        unknown = sorted(set(step) - set(FIELDS))
        if unknown:
            print(f"[warn] step {i}: ignoring unknown field(s) {', '.join(unknown)} "
                  f"(known: {', '.join(FIELDS)})", file=sys.stderr)
        step_errors = [f"step {i}: '{field}' must be a string"
                       for field in ("heading", "body", "caption")
                       if step.get(field) is not None and not isinstance(step[field], str)]
        image = step.get("image")
        images = [image] if isinstance(image, str) else image if image is not None else []
        if not isinstance(images, list) or not all(isinstance(p, str) and p for p in images):
            step_errors.append(f"step {i}: 'image' must be a path or a list of paths")
        if step_errors:
            errors += step_errors
            continue
        steps.append({
            "heading": (step.get("heading") or "").strip() or f"Step {i}",
            "body": step.get("body") or "",
            "caption": step.get("caption") or "",
            "images": [resolve_image(p, path.parent) for p in images],
        })
    if errors:
        raise StepsError("\n".join(errors))
    return steps


def resolve_image(image: str, steps_dir: Path):
    """Return (as_written, Path or None). Relative paths: current directory, then steps dir."""
    p = Path(image)
    for candidate in ([p] if p.is_absolute() else [p, steps_dir / p]):
        if candidate.is_file():
            return image, candidate
    return image, None


def paragraphs(body: str) -> list:
    """Split body text on blank lines; single newlines stay as line breaks."""
    parts = [p.strip("\n") for p in body.replace("\r\n", "\n").split("\n\n")]
    return [p for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------

DOCX_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
DOTX_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"


def open_template(path: Path):
    """Open a .docx or .dotx as a python-docx Document. Raises StepsError for anything else."""
    try:
        from docx import Document
        from docx.opc.exceptions import PackageNotFoundError
        from lxml.etree import XMLSyntaxError
    except ImportError:
        sys.exit("python-docx is not installed. Run: pip install python-docx")
    if not path.is_file():
        raise StepsError(f"--template file not found: {path}")
    try:
        data = path.read_bytes()
    except OSError as e:
        raise StepsError(f"--template cannot be read: {path} ({e.strerror or e})")
    try:
        # python-docx refuses a .dotx because its main part has the template content type,
        # so rewrite that one entry in memory and open the result.
        out = BytesIO()
        with zipfile.ZipFile(BytesIO(data)) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                content = zin.read(item.filename)
                if item.filename == "[Content_Types].xml":
                    content = content.replace(DOTX_MAIN.encode("utf-8"), DOCX_MAIN.encode("utf-8"))
                zout.writestr(item, content)
        out.seek(0)
        return Document(out)
    except (PackageNotFoundError, zipfile.BadZipFile, KeyError, ValueError, XMLSyntaxError,
            RuntimeError, NotImplementedError):  # the last two: an encrypted zip
        raise StepsError(f"--template is not a Word document (.docx or .dotx): {path}")


def clear_body(doc) -> None:
    """Remove every body child except the last w:sectPr (page setup, headers, footers)."""
    body = doc.element.body
    children = list(body)
    keep = children[-1] if children and children[-1].tag.endswith("}sectPr") else None
    for child in children:
        if child is not keep:
            body.remove(child)


def paragraph_style(doc, name: str, warned: set) -> str:
    """Return name, first adding a basic version of the style if the document lacks it."""
    from docx.enum.style import WD_STYLE_TYPE
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor
    try:
        doc.styles[name]
        return name
    except KeyError:
        pass
    style = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    style.base_style = doc.styles["Normal"]
    if name == "Title":
        style.font.bold, style.font.size = True, Pt(20)
    elif name == "Heading 2":
        style.font.bold, style.font.size = True, Pt(14)
        outline = OxmlElement("w:outlineLvl")  # level 2 heading, so the navigation pane lists it
        outline.set(qn("w:val"), "1")
        style.element.get_or_add_pPr().append(outline)
    elif name == "Caption":
        style.font.italic, style.font.size = True, Pt(9)
        style.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    if name not in warned:
        warned.add(name)
        print(f"[warn] template has no '{name}' style; added a basic one", file=sys.stderr)
    return name


ALIGN_NAMES = {"left": "LEFT", "center": "CENTER", "right": "RIGHT"}
STYLE_BLOCKS = (("title", "Title"), ("heading", "Heading 2"), ("caption", "Caption"))


def apply_document_style(doc, style: dict, has_template: bool, warned: set | None = None) -> list:
    """Apply a style file "document" section to the Normal, Title, Heading 2, and Caption styles.

    Creates a missing style first. Page settings apply only without a template. Returns warnings.
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Mm, Pt, RGBColor
    warned = set() if warned is None else warned
    warnings = []

    def set_font(st, font=None, size=None, color=None, bold=None, italic=None):
        if font is not None:
            st.font.name = font
        if size is not None:
            st.font.size = Pt(size)
        if color is not None:
            st.font.color.rgb = RGBColor(*parse_color(color))
        if bold is not None:
            st.font.bold = bold
        if italic is not None:
            st.font.italic = italic

    set_font(doc.styles["Normal"], style.get("font"), style.get("font_size"), style.get("color"))
    for key, name in STYLE_BLOCKS:
        block = style.get(key)
        if not block:
            continue
        st = doc.styles[paragraph_style(doc, name, warned)]
        if key == "caption" and not has_template:
            # The built-in caption look (italic gray 9 pt) stays for what the file does not name.
            set_font(st, size=9, color="#666666", bold=False, italic=True)
        set_font(st, block.get("font"), block.get("size"), block.get("color"),
                 block.get("bold"), block.get("italic"))
        if "align" in block:
            st.paragraph_format.alignment = getattr(WD_ALIGN_PARAGRAPH, ALIGN_NAMES[block["align"]])
        elif key == "caption" and not has_template:
            st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER  # the built-in look

    page = style.get("page")
    if page:
        if has_template:
            warnings.append("style file page settings are ignored with --template")
        else:
            section = doc.sections[0]
            if "size" in page:
                width, height = ((Inches(8.5), Inches(11)) if page["size"] == "letter"
                                 else (Mm(210), Mm(297)))
                section.page_width, section.page_height = width, height
            if "margins_in" in page:
                m = Inches(page["margins_in"])
                section.left_margin = section.right_margin = m
                section.top_margin = section.bottom_margin = m
    return warnings


def build_docx(title: str, steps: list, output: Path, opts: BuildOptions) -> list:
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.image.exceptions import UnrecognizedImageError
        from docx.image.image import Image as DocxImage
        from docx.shared import Inches, Pt, RGBColor
    except ImportError:
        sys.exit("python-docx is not installed. Run: pip install python-docx")

    problems, warned = [], set()
    templated = opts.document is not None
    if templated:
        doc = opts.document
        clear_body(doc)
    else:
        doc = Document()
        doc.styles["Normal"].font.size = Pt(11)

    for w in apply_document_style(doc, opts.style, templated, warned):
        print(f"[warn] {w}", file=sys.stderr)
    doc_style = opts.style or {}
    caption_styled = bool(doc_style.get("caption"))

    # With a template, the styles decide the look: no direct alignment or run formatting.
    # Without one, direct formatting stays only for what the style file does not name.
    title_para = doc.add_paragraph(title, style=paragraph_style(doc, "Title", warned))
    if not templated and "align" not in (doc_style.get("title") or {}):
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()  # spacer

    def placeholder(text):
        warn = doc.add_paragraph(text)
        warn.runs[0].font.color.rgb = RGBColor(0xCC, 0x00, 0x00)

    for step in steps:
        doc.add_paragraph(step["heading"], style=paragraph_style(doc, "Heading 2", warned))
        for para in paragraphs(step["body"]):
            doc.add_paragraph(para)

        for written, path in step["images"]:
            if path is None:
                problems.append(f"Image not found: {written}")
                placeholder(f"[Image not found: {written}]")
                continue
            try:
                info = DocxImage.from_file(str(path))
            except (UnrecognizedImageError, OSError) as e:
                detail = f" ({e})" if str(e) else ""
                problems.append(f"Image not readable (use PNG or JPEG): {written}{detail}")
                placeholder(f"[Image not readable: {written}]")
                continue
            # Natural screen size, shrunk to fit the page; never enlarged (blurry).
            w_in = info.px_width / SCREEN_DPI
            h_in = info.px_height / SCREEN_DPI
            scale = min(1.0, MAX_WIDTH_IN / w_in, MAX_HEIGHT_IN / h_in)
            doc.add_picture(str(path), width=Inches(w_in * scale), height=Inches(h_in * scale))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

        if step["caption"]:
            if templated or caption_styled:
                doc.add_paragraph(step["caption"], style=paragraph_style(doc, "Caption", warned))
            else:
                cap = doc.add_paragraph(step["caption"])
                cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cap.runs[0].font.italic = True
                cap.runs[0].font.size = Pt(9)
                cap.runs[0].font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        doc.add_paragraph()  # spacer between steps

    doc.save(str(output))
    return problems


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def md_link(path: Path, output: Path) -> str:
    try:
        rel = os.path.relpath(path.resolve(), output.resolve().parent)
    except ValueError:  # different drive on Windows
        rel = str(path.resolve())
    rel = rel.replace(os.sep, "/")
    return f"<{rel}>" if any(c in rel for c in " ()<>") else rel


def md_text(text: str) -> str:
    """Keep Markdown formatting the author wrote, but stop '<' from being read as HTML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_md(title: str, steps: list, output: Path, opts: BuildOptions) -> list:
    """Write Markdown and copy every image into <name>_images/ beside it.

    Copying keeps the tutorial working when the screenshots live in a temporary
    folder, and lets the .md and its images folder be shared together.
    """
    problems, out = [], [f"# {md_text(title)}", ""]
    images_dir = output.parent / f"{output.stem}_images"
    if images_dir.exists():
        shutil.rmtree(images_dir)  # drop images from an earlier build
    copied = {}  # source path -> copy, so an image used twice is copied once
    for step in steps:
        out += [f"## {md_text(step['heading'])}", ""]
        for para in paragraphs(step["body"]):
            out += [md_text(para).replace("\n", "  \n"), ""]  # two spaces = line break
        for written, path in step["images"]:
            if path is None:
                problems.append(f"Image not found: {written}")
                out += [f"**[Image not found: {md_text(written)}]**", ""]
                continue
            src = path.resolve()
            if src not in copied:
                images_dir.mkdir(parents=True, exist_ok=True)
                copy = images_dir / f"{len(copied) + 1:02d}-{path.name}"
                shutil.copyfile(src, copy)
                copied[src] = copy
            alt = md_text(step["caption"] or step["heading"]).replace("]", "\\]")
            out += [f"![{alt}]({md_link(copied[src], output)})", ""]
        if step["caption"]:
            out += [f"*{md_text(step['caption'])}*", ""]
    output.write_text("\n".join(out), encoding="utf-8", newline="\n")
    return problems


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

HTML_STYLE = """
body { font-family: system-ui, -apple-system, "Segoe UI", Arial, sans-serif; color: #1f2328;
       max-width: 860px; margin: 2rem auto; padding: 0 1rem; line-height: 1.55; }
h1 { text-align: center; }
h2 { margin-top: 2.5rem; border-bottom: 1px solid #d0d7de; padding-bottom: .3rem; }
figure { margin: 1rem 0; text-align: center; }
figure img { max-width: 100%; height: auto; border: 1px solid #d0d7de; border-radius: 4px; }
figcaption { font-size: .85rem; font-style: italic; color: #666; margin-top: .4rem; }
.missing { color: #c00; font-weight: bold; }
""".strip()


CSS_BLOCKS = (("h1", "title"), ("h2", "heading"), ("figcaption", "caption"))


def css_font(name: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", name):
        return name
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def css_hex(value) -> str:
    return "#%02X%02X%02X" % parse_color(value)


def style_css(style: dict) -> str:
    """Turn the style file's "document" section into CSS rules (page settings do not apply)."""
    def rule(selector, decls):
        if not decls:
            return ""
        return f"{selector} {{\n" + "".join(f"  {d};\n" for d in decls) + "}"

    def block_decls(block):
        decls = []
        if "font" in block:
            decls.append(f"font-family: {css_font(block['font'])}")
        if "size" in block:
            decls.append(f"font-size: {block['size']:g}pt")
        if "color" in block:
            decls.append(f"color: {css_hex(block['color'])}")
        if "bold" in block:
            decls.append(f"font-weight: {'bold' if block['bold'] else 'normal'}")
        if "italic" in block:
            decls.append(f"font-style: {'italic' if block['italic'] else 'normal'}")
        if "align" in block:
            decls.append(f"text-align: {block['align']}")
        return decls

    body = {}
    for src, dst in (("font", "font"), ("font_size", "size"), ("color", "color")):
        if src in style:
            body[dst] = style[src]
    rules = [rule("body", block_decls(body))]
    rules += [rule(sel, block_decls(style[key])) for sel, key in CSS_BLOCKS if style.get(key)]
    return "\n".join(r for r in rules if r)


def build_html(title: str, steps: list, output: Path, opts: BuildOptions) -> list:
    esc = html.escape
    problems = []
    extra_css = (opts.css or "").replace("</style", "<\\/style")
    page_css = "\n".join(c for c in (HTML_STYLE, style_css(opts.style), extra_css) if c.strip())
    parts = ["<!DOCTYPE html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             f"<title>{esc(title)}</title>", f"<style>\n{page_css}\n</style>", "</head>",
             "<body>", f"<h1>{esc(title)}</h1>"]
    for step in steps:
        parts.append(f"<section>\n<h2>{esc(step['heading'])}</h2>")
        for para in paragraphs(step["body"]):
            parts.append("<p>" + esc(para).replace("\n", "<br>\n") + "</p>")
        figure = []
        for written, path in step["images"]:
            mime = MIME.get(path.suffix.lower()) if path else None
            if path is None or mime is None:
                why = "not found" if path is None else "not a supported image type"
                problems.append(f"Image {why}: {written}")
                figure.append(f'<p class="missing">[Image {why}: {esc(written)}]</p>')
                continue
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            alt = esc(step["caption"] or step["heading"], quote=True)
            figure.append(f'<img src="data:{mime};base64,{data}" alt="{alt}">')
        if step["caption"]:
            figure.append(f"<figcaption>{esc(step['caption'])}</figcaption>")
        if figure:
            parts.append("<figure>\n" + "\n".join(figure) + "\n</figure>")
        parts.append("</section>")
    parts += ["</body>", "</html>", ""]
    output.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    return problems


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def check_writable(output: Path) -> None:
    """Raise PermissionError when an existing output is held open (for example, by a PDF viewer)."""
    if output.exists():
        with open(output, "ab"):
            pass


def build_pdf(title: str, steps: list, output: Path, opts: BuildOptions) -> list:
    """Build the tutorial in a temp folder, convert it with the engine main() picked, and copy
    the PDF to `output`. The temp folder is removed unless the engine fails."""
    check_writable(output)  # before building or starting an engine
    tmp = Path(tempfile.mkdtemp(prefix="document-website-pdf-"))
    keep = False
    try:
        pdf = tmp / "tutorial.pdf"
        try:
            if opts.pdf_engine == "chrome":
                page = tmp / "tutorial.html"
                problems = build_html(title, steps, page, opts)
                pdf_engines.html_to_pdf_chrome(page, pdf, opts.pdf_program)
            else:
                doc = tmp / "tutorial.docx"
                problems = build_docx(title, steps, doc, opts)
                if opts.pdf_engine == "word":
                    pdf_engines.docx_to_pdf_word(doc, pdf)
                else:
                    pdf_engines.docx_to_pdf_libreoffice(doc, pdf, opts.pdf_program)
        except pdf_engines.PdfEngineError as e:
            keep = True
            raise pdf_engines.PdfEngineError(f"{e}\nThe temp folder was kept for inspection: {tmp}")
        shutil.copyfile(pdf, output)
        return problems
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


BUILDERS = {".docx": build_docx, ".md": build_md, ".html": build_html, ".htm": build_html,
            ".pdf": build_pdf}


def read_css(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise StepsError(f"--css file not found: {path}")
    except UnicodeDecodeError as e:
        raise StepsError(f"--css file is not valid UTF-8 text: {path} ({e})")
    except OSError as e:
        raise StepsError(f"--css file could not be read: {path} ({e.strerror or e})")


def main():
    parser = argparse.ArgumentParser(
        description="Build a tutorial (.docx, .md, .html, or .pdf, from the --output extension) "
                    "from a steps JSON file.")
    parser.add_argument("--title",  required=True, help="Document title")
    parser.add_argument("--steps",  required=True, help="Path to the UTF-8 steps JSON file")
    parser.add_argument("--output", required=True,
                        help="Output path ending in .docx, .md, .html, or .pdf; parent folders are created")
    parser.add_argument("--template", metavar="FILE",
                        help="A .docx or .dotx whose styles, page setup, headers, and footers the "
                             ".docx output and the Word or LibreOffice .pdf output use; its body "
                             "is cleared")
    parser.add_argument("--style", metavar="FILE",
                        help="Style file (JSON); only its \"document\" section is used: fonts, sizes, "
                             "colors, alignment, and page setup")
    parser.add_argument("--css", metavar="FILE",
                        help="CSS file added after the built-in and style-file CSS (.html output, and "
                             ".pdf output built with Chrome)")
    parser.add_argument("--pdf-engine", choices=("auto",) + pdf_engines.ENGINES,
                        help="Program that makes a .pdf (default auto: Word, then LibreOffice, "
                             "then Chrome or Edge; Chrome first when --css is given without "
                             "--template). Only used for .pdf output")
    args = parser.parse_args()

    output = Path(args.output)
    builder = BUILDERS.get(output.suffix.lower())
    if builder is None:
        print(f"[error] --output must end in {', '.join(BUILDERS)}; got {output.name}", file=sys.stderr)
        sys.exit(2)
    opts = BuildOptions(template=Path(args.template) if args.template else None)
    ext = output.suffix.lower()
    try:
        steps = load_steps(Path(args.steps))
        if args.style:
            sections, style_warnings = load_style(args.style)
            errors, more = validate_document(sections["document"], args.style)
            for w in style_warnings + more:
                print(f"[warn] {w}", file=sys.stderr)
            if errors:
                raise StepsError("\n".join(errors))
            opts.style = sections["document"]
        if args.css:
            opts.css = read_css(Path(args.css))
            if ext not in (".html", ".htm", ".pdf"):
                print(f"[warn] --css applies to .html output (and .pdf output built with "
                      f"Chrome); ignored for {ext}", file=sys.stderr)
        if args.pdf_engine and ext != ".pdf":
            print("[warn] --pdf-engine applies to .pdf output; ignored", file=sys.stderr)
        if ext == ".pdf":
            found = pdf_engines.find_engines()  # through the module, so tests can replace it
            opts.pdf_engine = pdf_engines.pick_engine(
                args.pdf_engine or "auto", found,
                prefer_chrome=bool(args.css) and not opts.template)
            opts.pdf_program = found[opts.pdf_engine]
            if args.css and opts.pdf_engine != "chrome":
                print(f"[warn] --css applies to .pdf output only with the chrome engine; "
                      f"ignored with {opts.pdf_engine}", file=sys.stderr)
        uses_template = ext == ".docx" or (ext == ".pdf" and opts.pdf_engine != "chrome")
        if opts.template and uses_template:
            opts.document = open_template(opts.template)
        elif opts.template and ext == ".pdf":
            print("[warn] --template is ignored for .pdf output built with chrome; use "
                  "--pdf-engine word or libreoffice for a template", file=sys.stderr)
        elif opts.template:
            print(f"[warn] --template applies to .docx and .pdf output; ignored for {ext}",
                  file=sys.stderr)
    except (StepsError, StyleError, pdf_engines.PdfEngineError) as e:
        for line in str(e).splitlines():
            print(f"[error] {line}", file=sys.stderr)
        print("[error] Nothing was written.", file=sys.stderr)
        sys.exit(2)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        problems = builder(args.title, steps, output, opts)
    except pdf_engines.PdfEngineError as e:
        for line in str(e).splitlines():
            print(f"[error] {line}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"[error] cannot write {output}: permission denied. If it is open in Word "
              "or another program, close it and run again.", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"[error] cannot write {output}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Saved: {output}" + (f" (engine: {opts.pdf_engine})" if ext == ".pdf" else ""))
    if problems:
        for p in problems:
            print(f"[error] {p}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
