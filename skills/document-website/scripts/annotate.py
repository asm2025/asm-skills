#!/usr/bin/env python3
"""
annotate.py — Add arrows, numbered circles, highlight boxes, and labels to screenshots.

Usage:
    python3 annotate.py --input shot.png --output shot_annotated.png \
        --markers '[{"type":"arrow","to":[640,200]},{"type":"circle","at":[320,150],"label":"1"}]'

    python3 annotate.py --input shot.png --output shot_annotated.png \
        --markers-file markers.json
"""

import argparse
import json
import math
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is not installed. Run: pip install Pillow")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def auto_font(size: int):
    """Try to load a decent font; fall back to Pillow's default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def draw_arrow(draw: ImageDraw.ImageDraw, marker: dict):
    to = tuple(marker["to"])
    color = hex_to_rgb(marker.get("color", "#E53935"))
    lw = int(marker.get("width", 4))

    # Auto-compute tail offset (upper-left diagonal by default)
    if "from" in marker:
        frm = tuple(marker["from"])
    else:
        offset = 60
        angle = math.radians(225)  # lower-right → upper-left
        frm = (to[0] + offset * math.cos(angle), to[1] + offset * math.sin(angle))

    # Draw the line
    draw.line([frm, to], fill=color, width=lw)

    # Arrowhead
    dx, dy = to[0] - frm[0], to[1] - frm[1]
    length = math.hypot(dx, dy) or 1
    dx, dy = dx / length, dy / length
    head_len = lw * 4
    head_width = lw * 3
    lx = -dy
    ly = dx
    p1 = (to[0] - dx * head_len + lx * head_width,
          to[1] - dy * head_len + ly * head_width)
    p2 = (to[0] - dx * head_len - lx * head_width,
          to[1] - dy * head_len - ly * head_width)
    draw.polygon([to, p1, p2], fill=color)


def draw_circle(draw: ImageDraw.ImageDraw, marker: dict):
    cx, cy = marker["at"]
    label = str(marker.get("label", ""))
    r = int(marker.get("radius", 18))
    bg = hex_to_rgb(marker.get("bg", "#E53935"))
    fg = hex_to_rgb(marker.get("fg", "#FFFFFF"))
    font_size = max(10, int(r * 0.85))

    bbox = [cx - r, cy - r, cx + r, cy + r]
    draw.ellipse(bbox, fill=bg)

    if label:
        font = auto_font(font_size)
        # Measure text
        try:
            tx, ty, tx2, ty2 = draw.textbbox((0, 0), label, font=font)
            tw, th = tx2 - tx, ty2 - ty
        except AttributeError:
            tw, th = draw.textsize(label, font=font)
        draw.text((cx - tw / 2, cy - th / 2), label, fill=fg, font=font)


def draw_box(draw: ImageDraw.ImageDraw, marker: dict):
    x, y, w, h = marker["rect"]
    color = hex_to_rgb(marker.get("color", "#E53935"))
    lw = int(marker.get("width", 3))
    radius = int(marker.get("radius", 6))

    draw.rounded_rectangle([x, y, x + w, y + h],
                            radius=radius, outline=color, width=lw)


def draw_label(draw: ImageDraw.ImageDraw, marker: dict):
    x, y = marker["at"]
    text = str(marker.get("text", ""))
    bg = hex_to_rgb(marker.get("bg", "#E53935"))
    fg = hex_to_rgb(marker.get("fg", "#FFFFFF"))
    font_size = int(marker.get("font_size", 16))
    pad = 6

    font = auto_font(font_size)
    try:
        tx, ty, tx2, ty2 = draw.textbbox((0, 0), text, font=font)
        tw, th = tx2 - tx, ty2 - ty
    except AttributeError:
        tw, th = draw.textsize(text, font=font)

    draw.rounded_rectangle([x, y, x + tw + pad * 2, y + th + pad * 2],
                            radius=4, fill=bg)
    draw.text((x + pad, y + pad), text, fill=fg, font=font)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

DRAWERS = {
    "arrow":  draw_arrow,
    "circle": draw_circle,
    "box":    draw_box,
    "label":  draw_label,
}


def annotate(input_path: str, output_path: str, markers: list):
    img = Image.open(input_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for m in markers:
        mtype = m.get("type")
        if mtype not in DRAWERS:
            print(f"[warn] Unknown marker type '{mtype}', skipping.", file=sys.stderr)
            continue
        DRAWERS[mtype](draw, m)

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    combined.save(output_path)
    print(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Annotate a screenshot with markers.")
    parser.add_argument("--input",  required=True, help="Input PNG path")
    parser.add_argument("--output", required=True, help="Output PNG path")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--markers",      help="JSON array string of markers")
    group.add_argument("--markers-file", help="Path to a JSON file containing the markers array")
    args = parser.parse_args()

    if args.markers_file:
        with open(args.markers_file) as f:
            markers = json.load(f)
    else:
        markers = json.loads(args.markers)

    annotate(args.input, args.output, markers)


if __name__ == "__main__":
    main()
