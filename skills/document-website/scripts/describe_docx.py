#!/usr/bin/env python3
"""
describe_docx.py - print what a Word document looks like, so the agent can match it.

Usage: describe_docx.py <file.docx|file.dotx>

Prints page setup per section, header and footer text, the paragraph styles in use with
their resolved font, size, color, bold, and italic, an outline of the title and headings,
and image and table counts. Exit 0; a missing or non-Word file exits 2.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_docx import StepsError, open_template  # noqa: E402


def resolve(style, getter):
    """First non-None value of getter(style) up the base_style chain."""
    seen = 0
    while style is not None and seen < 50:
        value = getter(style)
        if value is not None:
            return value
        style = style.base_style
        seen += 1
    return None


def flag(value) -> str:
    return "-" if value is None else ("yes" if value else "no")


def describe_style(style) -> str:
    font = resolve(style, lambda s: s.font.name)
    size = resolve(style, lambda s: s.font.size)
    color = resolve(style, lambda s: s.font.color.rgb if s.font.color is not None
                    and s.font.color.type is not None else None)
    bold = resolve(style, lambda s: s.font.bold)
    italic = resolve(style, lambda s: s.font.italic)
    return (f"font {font or '-'}, "
            f"{'-' if size is None else format(size.pt, 'g')} pt, "
            f"color {'#' + str(color).upper() if color is not None else '-'}, "
            f"bold {flag(bold)}, italic {flag(italic)}")


def part_text(part) -> str:
    return " ".join(p.text.strip() for p in part.paragraphs if p.text.strip())


def describe(doc) -> list[str]:
    lines = []
    for sec in doc.sections:
        lines.append(f"page: {sec.page_width.inches:.2f} x {sec.page_height.inches:.2f} in, margins "
                     f"{sec.left_margin.inches:.2f}/{sec.right_margin.inches:.2f}/"
                     f"{sec.top_margin.inches:.2f}/{sec.bottom_margin.inches:.2f} in")
        lines.append(f"header: {part_text(sec.header)}")
        lines.append(f"footer: {part_text(sec.footer)}")
    used = {}
    for p in doc.paragraphs:
        used.setdefault(p.style.name, p.style)
    lines.append("styles used:")
    for name, style in used.items():
        lines.append(f"  {name}: {describe_style(style)}")
    lines.append("outline:")
    for p in doc.paragraphs:
        name = p.style.name
        m = re.fullmatch(r"Heading (\d)", name)
        if name == "Title":
            lines.append(f"  {p.text}")
        elif m:
            lines.append(f"{'  ' * (int(m.group(1)) + 1)}{p.text}")
    lines.append(f"images: {len(doc.inline_shapes)}")
    lines.append(f"tables: {len(doc.tables)}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Describe the page setup, styles, and outline of a Word document.")
    ap.add_argument("file", help=".docx or .dotx file")
    args = ap.parse_args()
    try:
        doc = open_template(Path(args.file))
    except StepsError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(describe(doc)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
