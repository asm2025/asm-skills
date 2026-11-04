#!/usr/bin/env python3
"""
annotate.py - Add arrows, numbered circles, highlight boxes, and labels to screenshots.

Usage:
    python3 annotate.py --input shot.png --output shot_annotated.png \
        --markers '[{"type":"arrow","to":[640,200]},{"type":"circle","at":[320,150],"label":"1"}]'

    python3 annotate.py --input shot.png --output shot_annotated.png \
        --markers-file markers.json

    python3 annotate.py --input shot.png --output shot_annotated.png \
        --markers-file markers.json --style style.json --color "#1565C0"

Marker files are read as UTF-8. Coordinates are pixels from the image's top-left
corner. See references/annotation-spec.md for every marker type and field.

A marker field it leaves out is filled from, in order: --color/--bg/--fg, the
style file's markers section (--style), then the built-in defaults.

Exit codes: 0 saved (warnings may be printed), 1 could not read or write a file,
2 invalid arguments, style file, or markers (nothing is written).
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

try:
    from PIL import Image, ImageColor, ImageDraw, ImageFont, features
except ImportError:
    sys.exit("Pillow is not installed. Run: pip install Pillow")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contrast import choose, ratio, ring, score, text_on  # noqa: E402
from style_file import (MARKER_FIELDS, StyleError, load_style,  # noqa: E402
                        parse_color, validate_markers)


DEFAULT_RED = "#E53935"
WHITE = "#FFFFFF"

# Tried in order; the first font that has every character of a text wins.
# Bold Latin fonts first so labels read well on screenshots, then fonts that
# cover symbols and CJK. Missing files are skipped.
FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/seguisym.ttf",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/Nirmala.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Apple Symbols.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

RTL_BIDI = {"R", "AL", "AN"}


class MarkerError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

_font_cache = {}
_glyph_cache = {}


def _load(path: str, size: int):
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except OSError:
            _font_cache[key] = None
    return _font_cache[key]


def _render(font, ch: str):
    left, top, right, bottom = font.getbbox(ch)
    w, h = max(1, right - left), max(1, bottom - top)
    img = Image.new("L", (w, h))
    ImageDraw.Draw(img).text((-left, -top), ch, font=font, fill=255)
    return img.size, img.tobytes()


def missing_chars(path: str, font, text: str) -> list:
    """Characters of text that the font draws as its 'missing glyph' box."""
    out = []
    notdef = None
    for ch in dict.fromkeys(text):
        if ch.isspace() or unicodedata.category(ch).startswith("C"):
            continue
        key = (path, ch)
        if key not in _glyph_cache:
            if notdef is None:
                notdef = _render(font, "\U0010FFFD")  # private use: never in real fonts
            _glyph_cache[key] = _render(font, ch) == notdef
        if _glyph_cache[key]:
            out.append(ch)
    return out


def _fc_match(text: str):
    if not shutil.which("fc-match"):
        return None
    chars = " ".join(f"{ord(c):x}" for c in dict.fromkeys(text) if not c.isspace())
    try:
        res = subprocess.run(["fc-match", "-f", "%{file}", f":charset={chars}"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout.strip() or None


def pick_font(text: str, size: int, override: str = None):
    """Return (font, font_path, missing_characters) for drawing text."""
    paths = [override] if override else [p for p in FONT_CANDIDATES if Path(p).exists()]
    best = None
    for path in paths:
        font = _load(path, size)
        if font is None:
            continue
        missing = missing_chars(path, font, text)
        if not missing:
            return font, path, []
        if best is None or len(missing) < len(best[2]):
            best = (font, path, missing)
    if not override:
        path = _fc_match(text)
        if path and Path(path).exists():
            font = _load(path, size)
            if font is not None:
                missing = missing_chars(path, font, text)
                if not missing or best is None or len(missing) < len(best[2]):
                    best = (font, path, missing)
    if best:
        return best
    try:
        return ImageFont.load_default(size), "Pillow default font", []
    except TypeError:  # Pillow < 10.1 cannot size the default font
        return ImageFont.load_default(), "Pillow default font", []


def auto_font(size: int):
    """The font used for plain Latin text (kept for callers that only need one)."""
    return pick_font("Ag", size)[0]


def measure(draw: ImageDraw.ImageDraw, text: str, font):
    """Return (x_offset, y_offset, width, height) of the drawn glyphs.

    The offsets are where the glyphs start relative to the text origin; fonts
    leave space above the glyphs, so drawing at the origin sits text low.
    """
    try:
        tx, ty, tx2, ty2 = draw.textbbox((0, 0), text, font=font)
        return tx, ty, tx2 - tx, ty2 - ty
    except AttributeError:  # Pillow < 8: no textbbox
        tw, th = draw.textsize(text, font=font)
        return 0, 0, tw, th


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def point(m: dict, field: str, required: bool = True):
    v = m.get(field)
    if v is None:
        if required:
            raise MarkerError(f"missing field '{field}' (expected [x, y])")
        return None
    if not (isinstance(v, (list, tuple)) and len(v) == 2 and all(map(_num, v))):
        raise MarkerError(f"field '{field}' must be [x, y] numbers, got {json.dumps(v)}")
    return float(v[0]), float(v[1])


def integer(m: dict, field: str, default: int, minimum: int = 1):
    v = m.get(field, default)
    if not _num(v) or v < minimum:
        raise MarkerError(f"field '{field}' must be a number >= {minimum}, got {json.dumps(v)}")
    return int(v)


def color(m: dict, field: str, default: str):
    v = m.get(field, default)
    try:
        return ImageColor.getrgb(str(v))[:3]
    except ValueError:
        raise MarkerError(f"field '{field}' is not a color: {json.dumps(v)} "
                          "(use a CSS hex value like \"#E53935\" or a CSS color name)")


def text_field(m: dict, field: str, required: bool):
    if field not in m:
        if required:
            raise MarkerError(f"missing field '{field}'")
        return ""
    v = m[field]
    if not isinstance(v, (str, int, float)) or isinstance(v, bool):
        raise MarkerError(f"field '{field}' must be text, got {json.dumps(v)}")
    return str(v)


class Canvas:
    """The overlay plus the context drawers need: image size, font override, warnings."""

    def __init__(self, size, font_override):
        self.size = size
        self.overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.overlay)
        self.font_override = font_override
        self.warnings = []
        self.where = "marker"  # set by annotate() before each marker is drawn

    def prepare_text(self, text: str) -> str:
        """Return text ready to draw, shaping right-to-left scripts when Pillow cannot."""
        if features.check("raqm") or not any(
                unicodedata.bidirectional(c) in RTL_BIDI for c in text):
            return text  # libraqm shapes and orders the text itself
        try:
            import arabic_reshaper
            try:
                from bidi import get_display
            except ImportError:  # python-bidi < 0.5
                from bidi.algorithm import get_display
        except ImportError:
            self.warnings.append(
                f"{self.where}: right-to-left text needs Pillow with libraqm, or "
                "`pip install arabic-reshaper python-bidi`; neither is available, so "
                "letters will be drawn unjoined, left to right.")
            return text
        return get_display(arabic_reshaper.reshape(text))

    def font_for(self, text: str, size: int):
        font, path, missing = pick_font(text, size, self.font_override)
        if missing:
            self.warnings.append(
                f"{self.where}: no available font has {' '.join(missing)}; "
                "it will draw as a box. Pass --font with a font that has it.")
        return font


# ---------------------------------------------------------------------------
# Drawing primitives. Each validates its marker, draws it, and returns the
# bounding box it covers so the caller can warn about markers off the image.
# ---------------------------------------------------------------------------

def draw_arrow(c: Canvas, m: dict):
    to = point(m, "to")
    frm = point(m, "from", required=False)
    col = color(m, "color", DEFAULT_RED)
    lw = integer(m, "width", 4)
    head_len, head_w = lw * 4, lw * 3

    if frm is None:
        # Tail up and to the left of the tip; flip an axis that would leave the image.
        off = max(60, head_len * 3) * math.cos(math.radians(45))
        w, h = c.size
        fx = to[0] - off if to[0] - off >= 0 or to[0] + off > w else to[0] + off
        fy = to[1] - off if to[1] - off >= 0 or to[1] + off > h else to[1] + off
        frm = (fx, fy)

    dx, dy = to[0] - frm[0], to[1] - frm[1]
    length = math.hypot(dx, dy)
    if length < 1:
        raise MarkerError("'from' and 'to' are the same point")
    ux, uy = dx / length, dy / length
    # End the shaft inside the head so its square end cannot poke past the tip.
    shaft_end = (to[0] - ux * head_len * 0.7, to[1] - uy * head_len * 0.7)
    if length > head_len:
        c.draw.line([frm, shaft_end], fill=col, width=lw)
    lx, ly = -uy, ux
    base = (to[0] - ux * head_len, to[1] - uy * head_len)
    p1 = (base[0] + lx * head_w, base[1] + ly * head_w)
    p2 = (base[0] - lx * head_w, base[1] - ly * head_w)
    c.draw.polygon([to, p1, p2], fill=col)
    xs = [frm[0], to[0], p1[0], p2[0]]
    ys = [frm[1], to[1], p1[1], p2[1]]
    return min(xs) - lw, min(ys) - lw, max(xs) + lw, max(ys) + lw


def draw_circle(c: Canvas, m: dict):
    cx, cy = point(m, "at")
    label = text_field(m, "label", required=False)
    r = integer(m, "radius", 18)
    bg = color(m, "bg", DEFAULT_RED)
    fg = color(m, "fg", WHITE)

    c.draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg)
    if label:
        label = c.prepare_text(label)
        font = c.font_for(label, max(10, int(r * 0.85)))
        tx, ty, tw, th = measure(c.draw, label, font)
        # Subtract the bbox offset so the glyphs, not the text origin, are centered.
        c.draw.text((cx - tw / 2 - tx, cy - th / 2 - ty), label, fill=fg, font=font)
    return cx - r, cy - r, cx + r, cy + r


def draw_box(c: Canvas, m: dict):
    rect = m.get("rect")
    if not (isinstance(rect, (list, tuple)) and len(rect) == 4 and all(map(_num, rect))):
        raise MarkerError(f"field 'rect' must be [x, y, width, height] numbers, got {json.dumps(rect)}")
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        raise MarkerError(f"'rect' width and height must be positive, got {w} x {h}")
    col = color(m, "color", DEFAULT_RED)
    lw = integer(m, "width", 3)
    radius = integer(m, "radius", 6, minimum=0)
    c.draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, outline=col, width=lw)
    return x, y, x + w, y + h


def draw_label(c: Canvas, m: dict):
    x, y = point(m, "at")
    text = text_field(m, "text", required=True)
    if not text.strip():
        raise MarkerError("field 'text' is empty")
    bg = color(m, "bg", DEFAULT_RED)
    fg = color(m, "fg", WHITE)
    pad = 6

    text = c.prepare_text(text)
    font = c.font_for(text, integer(m, "font_size", 16))
    tx, ty, tw, th = measure(c.draw, text, font)
    c.draw.rounded_rectangle([x, y, x + tw + pad * 2, y + th + pad * 2], radius=4, fill=bg)
    c.draw.text((x + pad - tx, y + pad - ty), text, fill=fg, font=font)
    return x, y, x + tw + pad * 2, y + th + pad * 2


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

DRAWERS = {
    "arrow":  draw_arrow,
    "circle": draw_circle,
    "box":    draw_box,
    "label":  draw_label,
}


def resolve(m: dict, mtype: str, defaults: dict) -> dict:
    """Return the marker with missing fields filled from the defaults.

    Order, first match wins: the marker itself, the command line
    (defaults["cli"]: color, bg, fg), the style file's per-type block, the style
    file's "defaults" block. Only fields the marker type accepts are filled;
    anything still missing is left for the drawer's built-in default.
    """
    out = dict(m)
    cli = defaults.get("cli") or {}
    style = defaults.get("style") or {}
    sources = (cli, style.get(mtype) or {}, style.get("defaults") or {})
    for field in MARKER_FIELDS[mtype]:
        if field in out:
            continue
        for src in sources:
            if field in src:
                out[field] = src[field]
                break
    return out


# The field that carries each marker type's main color.
MAIN_COLOR = {"arrow": "color", "box": "color", "circle": "bg", "label": "bg"}
RING_WIDTH = 3


def _hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def settle_colors(canvas: Canvas, scratch: Canvas, img, mtype: str, marker: dict,
                  min_contrast: float, palette) -> dict:
    """Return the marker with colors swapped where they would blend into the screenshot.

    The marker is drawn once on the scratch canvas to learn its footprint. Only a
    crop around it is measured, so a tall full-page screenshot stays fast. The
    scratch canvas is cleared again and its warnings are discarded: font and
    right-to-left warnings come from the real draw.
    """
    scratch.where = canvas.where
    bx0, by0, bx1, by1 = DRAWERS[mtype](scratch, marker)
    scratch.warnings.clear()
    pad = RING_WIDTH + 1
    w, h = img.size
    box = (max(0, math.floor(bx0) - pad), max(0, math.floor(by0) - pad),
           min(w, math.ceil(bx1) + pad + 1), min(h, math.ceil(by1) + pad + 1))
    if box[0] >= box[2] or box[1] >= box[3]:
        return marker  # entirely off the image: nothing to measure
    alpha = scratch.overlay.crop(box).getchannel("A")
    scratch.overlay.paste((0, 0, 0, 0), box)  # clear it for the next marker
    mask = ring(alpha, RING_WIDTH)
    background = img.crop(box).convert("RGB")

    field = MAIN_COLOR[mtype]
    out = dict(marker)
    old = color(marker, field, DEFAULT_RED)
    old_score = score(background, mask, old)
    new, new_score = choose(background, mask, old, palette or [], min_contrast,
                            preferred_score=old_score)
    if new != old:
        canvas.warnings.append(
            f"{canvas.where}: {field} {_hex(old)} has {old_score:.1f}:1 contrast on the "
            f"background; drew {_hex(new)} instead ({new_score:.1f}:1).")
        out[field] = _hex(new)
    else:
        out[field] = _hex(old)

    if mtype in ("circle", "label"):
        has_text = bool(str(marker.get("label" if mtype == "circle" else "text", "")).strip())
        if has_text:
            fg = color(marker, "fg", WHITE)
            fill = color(out, "bg", DEFAULT_RED)
            drawn = text_on(fill, fg)
            if drawn != fg:
                canvas.warnings.append(
                    f"{canvas.where}: fg {_hex(fg)} has {ratio(fg, fill):.1f}:1 contrast on "
                    f"bg {_hex(fill)}; drew {_hex(drawn)} instead ({ratio(drawn, fill):.1f}:1).")
                out["fg"] = _hex(drawn)
    return out


def annotate(input_path: str, output_path: str, markers: list, font: str = None,
             defaults: dict = None, auto_contrast: bool = True,
             min_contrast: float = 3.0, palette: list = None):
    """Draw markers onto input_path and save output_path.

    defaults is {"cli": {...}, "style": markers_section}; see resolve().
    With auto_contrast on (and not switched off for a marker), a marker color
    that would blend into the screenshot is swapped for one that stands out,
    using min_contrast and the style palette; each swap adds a warning.

    Returns the list of warnings. Raises MarkerError (nothing written) when a
    marker is invalid, and OSError when a file cannot be read or written.
    """
    defaults = defaults or {}
    if not isinstance(markers, list):
        raise MarkerError(f"markers must be a JSON array, got {type(markers).__name__}")
    img = Image.open(input_path)
    img.load()
    img = img.convert("RGBA")
    canvas = Canvas(img.size, font)
    scratch = None  # allocated on the first marker that needs measuring
    w, h = img.size
    errors = []

    for i, m in enumerate(markers, start=1):
        if not isinstance(m, dict):
            errors.append(f"marker {i}: must be an object, got {json.dumps(m)}")
            continue
        mtype = m.get("type")
        if mtype not in DRAWERS:
            canvas.warnings.append(f"marker {i}: unknown type {mtype!r}, skipped "
                                   f"(known: {', '.join(DRAWERS)})")
            continue
        canvas.where = f"marker {i} ({mtype})"
        try:
            marker = resolve(m, mtype, defaults)
            if auto_contrast and marker.get("auto_contrast", True) is not False:
                if scratch is None:
                    scratch = Canvas(img.size, font)
                marker = settle_colors(canvas, scratch, img, mtype, marker,
                                       min_contrast, palette)
            x0, y0, x1, y1 = DRAWERS[mtype](canvas, marker)
        except MarkerError as e:
            errors.append(f"marker {i} ({mtype}): {e}")
            continue
        if x1 < 0 or y1 < 0 or x0 > w or y0 > h:
            canvas.warnings.append(
                f"marker {i} ({mtype}) is entirely outside the {w}x{h} image "
                f"(covers {round(x0)},{round(y0)} to {round(x1)},{round(y1)}). "
                "Coordinates are image pixels; for a full-page or device-scale screenshot, "
                "add the scroll offset or multiply by the scale.")
        elif x0 < 0 or y0 < 0 or x1 > w or y1 > h:
            canvas.warnings.append(
                f"marker {i} ({mtype}) is cut off at the edge of the {w}x{h} image "
                f"(covers {round(x0)},{round(y0)} to {round(x1)},{round(y1)}).")

    if errors:
        raise MarkerError("\n".join(errors))

    combined = Image.alpha_composite(img, canvas.overlay).convert("RGB")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    combined.save(out)
    return canvas.warnings


def main():
    parser = argparse.ArgumentParser(
        description="Annotate a screenshot with markers. See references/annotation-spec.md.")
    parser.add_argument("--input",  required=True, help="Input image path (PNG or JPEG)")
    parser.add_argument("--output", required=True, help="Output image path; parent folders are created")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--markers",      help="JSON array string of markers")
    group.add_argument("--markers-file", help="Path to a UTF-8 JSON file containing the markers array")
    parser.add_argument("--font", help="TrueType/OpenType font file for all text, instead of the automatic choice")
    parser.add_argument("--style", help="Style file (JSON); its markers section sets default colors and sizes")
    parser.add_argument("--color", help="Default color for arrows and boxes that set none")
    parser.add_argument("--bg", help="Default fill color for circles and labels that set none")
    parser.add_argument("--fg", help="Default text color for circles and labels that set none")
    parser.add_argument("--no-auto-contrast", action="store_true",
                        help="Never replace a marker color for low contrast on the screenshot")
    args = parser.parse_args()

    cli = {}
    for opt in ("color", "bg", "fg"):
        value = getattr(args, opt)
        if value is None:
            continue
        try:
            parse_color(value)
        except StyleError:
            print(f"[error] --{opt} is not a color: {json.dumps(value)} (use a CSS hex "
                  "value like \"#E53935\" or a CSS color name)", file=sys.stderr)
            sys.exit(2)
        cli[opt] = value

    style_warnings, style_errors = [], []
    try:
        sections, style_warnings = load_style(args.style)
        style_errors, more = validate_markers(sections["markers"], args.style)
        style_warnings += more
    except StyleError as e:
        style_errors = [str(e)]
    if style_errors:
        for w in style_warnings:
            print(f"[warn] {w}", file=sys.stderr)
        for line in style_errors:
            print(f"[error] {line}", file=sys.stderr)
        print("[error] Nothing was written.", file=sys.stderr)
        sys.exit(2)
    style = sections["markers"]

    if args.font:
        if not Path(args.font).is_file():
            print(f"[error] --font file not found: {args.font}", file=sys.stderr)
            sys.exit(2)
        if _load(args.font, 16) is None:
            print(f"[error] --font is not a TrueType/OpenType font: {args.font}", file=sys.stderr)
            sys.exit(2)
    try:
        if args.markers_file:
            with open(args.markers_file, encoding="utf-8-sig") as f:
                markers = json.load(f)
        else:
            markers = json.loads(args.markers)
    except FileNotFoundError:
        print(f"[error] markers file not found: {args.markers_file}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        src = args.markers_file or "--markers"
        hint = "" if args.markers_file else (
            " Shell quoting often breaks inline JSON (especially in PowerShell); "
            "write the array to a file and pass --markers-file instead.")
        print(f"[error] {src} is not valid JSON: {e}.{hint}", file=sys.stderr)
        sys.exit(2)

    if not Path(args.input).is_file():
        print(f"[error] input image not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    try:
        warnings = annotate(
            args.input, args.output, markers, args.font,
            defaults={"cli": cli, "style": style},
            auto_contrast=not args.no_auto_contrast and style.get("auto_contrast", True),
            min_contrast=style.get("min_contrast", 3.0),
            palette=style.get("palette"))
    except MarkerError as e:
        for line in str(e).splitlines():
            print(f"[error] {line}", file=sys.stderr)
        print("[error] Nothing was written.", file=sys.stderr)
        sys.exit(2)
    except OSError as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)

    for w in style_warnings + warnings:
        print(f"[warn] {w}", file=sys.stderr)
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
