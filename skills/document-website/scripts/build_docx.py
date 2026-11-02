#!/usr/bin/env python3
"""
build_docx.py - Assemble a step-by-step tutorial from a steps JSON file.

The output format follows the --output extension:
    .docx         Word document (needs python-docx)
    .md           Markdown, linking images by path relative to the output file
    .html / .htm  one self-contained HTML file with the images embedded

Usage:
    python3 build_docx.py \
        --title  "My App - Getting Started" \
        --steps  steps.json \
        --output tutorial.docx

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

A relative image path is looked up from the current directory first, then from
the folder that holds steps.json.

Exit codes: 0 saved, 1 saved but an image was missing or unreadable (each one is
replaced by a red "[Image not found: ...]" line and listed on stderr), or the
output could not be written, 2 invalid arguments or steps (nothing written).
"""

import argparse
import base64
import html
import json
import os
import sys
from pathlib import Path

FIELDS = ("heading", "body", "image", "caption")
MAX_WIDTH_IN, MAX_HEIGHT_IN, SCREEN_DPI = 6.0, 8.0, 96
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}


class StepsError(ValueError):
    pass


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

def build_docx(title: str, steps: list, output: Path) -> list:
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.image.exceptions import UnrecognizedImageError
        from docx.image.image import Image as DocxImage
        from docx.shared import Inches, Pt, RGBColor
    except ImportError:
        sys.exit("python-docx is not installed. Run: pip install python-docx")

    problems = []
    doc = Document()
    doc.styles["Normal"].font.size = Pt(11)

    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()  # spacer

    def placeholder(text):
        warn = doc.add_paragraph(text)
        warn.runs[0].font.color.rgb = RGBColor(0xCC, 0x00, 0x00)

    for step in steps:
        doc.add_heading(step["heading"], level=2)
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


def build_md(title: str, steps: list, output: Path) -> list:
    problems, out = [], [f"# {md_text(title)}", ""]
    for step in steps:
        out += [f"## {md_text(step['heading'])}", ""]
        for para in paragraphs(step["body"]):
            out += [md_text(para).replace("\n", "  \n"), ""]  # two spaces = line break
        for written, path in step["images"]:
            if path is None:
                problems.append(f"Image not found: {written}")
                out += [f"**[Image not found: {md_text(written)}]**", ""]
            else:
                alt = md_text(step["caption"] or step["heading"]).replace("]", "\\]")
                out += [f"![{alt}]({md_link(path, output)})", ""]
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


def build_html(title: str, steps: list, output: Path) -> list:
    esc = html.escape
    problems = []
    parts = ["<!DOCTYPE html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             f"<title>{esc(title)}</title>", f"<style>\n{HTML_STYLE}\n</style>", "</head>",
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


BUILDERS = {".docx": build_docx, ".md": build_md, ".html": build_html, ".htm": build_html}


def main():
    parser = argparse.ArgumentParser(
        description="Build a tutorial (.docx, .md, or .html, from the --output extension) "
                    "from a steps JSON file.")
    parser.add_argument("--title",  required=True, help="Document title")
    parser.add_argument("--steps",  required=True, help="Path to the UTF-8 steps JSON file")
    parser.add_argument("--output", required=True,
                        help="Output path ending in .docx, .md, or .html; parent folders are created")
    args = parser.parse_args()

    output = Path(args.output)
    builder = BUILDERS.get(output.suffix.lower())
    if builder is None:
        print(f"[error] --output must end in {', '.join(BUILDERS)}; got {output.name}", file=sys.stderr)
        sys.exit(2)
    try:
        steps = load_steps(Path(args.steps))
    except StepsError as e:
        for line in str(e).splitlines():
            print(f"[error] {line}", file=sys.stderr)
        print("[error] Nothing was written.", file=sys.stderr)
        sys.exit(2)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        problems = builder(args.title, steps, output)
    except PermissionError:
        print(f"[error] cannot write {output}: permission denied. If it is open in Word "
              "or another program, close it and run again.", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"[error] cannot write {output}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Saved: {output}")
    if problems:
        for p in problems:
            print(f"[error] {p}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
