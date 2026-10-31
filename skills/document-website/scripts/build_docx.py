#!/usr/bin/env python3
"""
build_docx.py — Assemble a step-by-step tutorial Word document from a steps JSON file.

Usage:
    python3 build_docx.py \
        --title  "My App – Getting Started" \
        --steps  steps.json \
        --output tutorial.docx

steps.json format:
[
  {
    "heading": "Step 1: Log in",
    "body":    "Navigate to the login page and enter your credentials.",
    "image":   "./docs/screenshots/login_annotated.png",
    "caption": "Login screen"           <- optional
  },
  ...
]
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    sys.exit("python-docx is not installed. Run: pip install python-docx")


def build(title: str, steps: list, output: str):
    doc = Document()

    # ── Title ──────────────────────────────────────────────────────────────
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()  # spacer

    # ── Steps ──────────────────────────────────────────────────────────────
    for i, step in enumerate(steps, start=1):
        heading = step.get("heading") or f"Step {i}"
        body    = step.get("body", "")
        image   = step.get("image")
        caption = step.get("caption", "")

        # Step heading
        doc.add_heading(heading, level=2)

        # Body text
        if body:
            para = doc.add_paragraph(body)
            para.style.font.size = Pt(11)

        # Screenshot
        if image:
            img_path = Path(image)
            if img_path.exists():
                doc.add_picture(str(img_path), width=Inches(6.0))
                last_para = doc.paragraphs[-1]
                last_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                warn = doc.add_paragraph(f"[Image not found: {image}]")
                warn.runs[0].font.color.rgb = RGBColor(0xCC, 0x00, 0x00)

        # Caption
        if caption:
            cap = doc.add_paragraph(caption)
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.runs[0].font.italic = True
            cap.runs[0].font.size = Pt(9)
            cap.runs[0].font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        doc.add_paragraph()  # spacer between steps

    # ── Save ───────────────────────────────────────────────────────────────
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build a tutorial .docx from a steps JSON file.")
    parser.add_argument("--title",  required=True, help="Document title")
    parser.add_argument("--steps",  required=True, help="Path to steps JSON file")
    parser.add_argument("--output", required=True, help="Output .docx path")
    args = parser.parse_args()

    with open(args.steps) as f:
        steps = json.load(f)

    build(args.title, steps, args.output)


if __name__ == "__main__":
    main()
