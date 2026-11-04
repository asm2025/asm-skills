#!/usr/bin/env python3
"""
contrast.py - WCAG contrast helpers that keep annotate.py markers readable.

annotate.py draws each marker once on a scratch canvas, takes a thin ring of
screenshot pixels just outside the drawn shape, and asks choose() whether the
marker color stands out against that ring. Everything here works on small
crops, never on the whole screenshot.
"""

from PIL import Image, ImageChops, ImageFilter

BUILTIN_PALETTE = ["#E53935", "#1565C0", "#FDD835", "#000000", "#FFFFFF"]

# Marker text is bold and large, so the WCAG large-text minimum applies. This
# does not follow min_contrast.
TEXT_MIN_CONTRAST = 3.0

_BLACK = (0, 0, 0)
_WHITE = (255, 255, 255)
_lum_cache = {}


def _channel(v: int) -> float:
    c = v / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb) -> float:
    """WCAG relative luminance of an (r, g, b) color."""
    key = tuple(rgb[:3])
    lum = _lum_cache.get(key)
    if lum is None:
        r, g, b = key
        lum = 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)
        if len(_lum_cache) < 100000:
            _lum_cache[key] = lum
    return lum


def ratio(a, b) -> float:
    """WCAG contrast ratio of two colors, from 1 to 21."""
    la, lb = luminance(a), luminance(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def ring(footprint: Image.Image, width: int = 3) -> Image.Image:
    """Mask (mode L) of pixels within width of the footprint but outside it."""
    shape = footprint.convert("L").point(lambda v: 255 if v else 0)
    grown = shape.filter(ImageFilter.MaxFilter(2 * width + 1))
    return ImageChops.subtract(grown, shape)


def score(background: Image.Image, mask: Image.Image, rgb):
    """20th percentile of the contrast ratio of rgb against the masked pixels.

    Returns None when the mask selects no pixel. background and mask are the
    same size.
    """
    pixels = background.convert("RGB").getdata()
    ratios = [ratio(rgb, px) for px, m in zip(pixels, mask.getdata()) if m]
    if not ratios:
        return None
    ratios.sort()
    return ratios[int(0.2 * (len(ratios) - 1))]


def choose(background: Image.Image, mask: Image.Image, preferred_rgb, palette,
           min_contrast: float):
    """Return (rgb, score) for the color to draw.

    The preferred color when it reaches min_contrast; otherwise the first color
    of palette (the style palette, then BUILTIN_PALETTE) that does; otherwise the
    highest-scoring candidate, the preferred color winning ties. With an empty
    mask there is nothing to measure, so the preferred color is kept (score None).
    """
    preferred = tuple(preferred_rgb[:3])
    best = score(background, mask, preferred)
    if best is None or best >= min_contrast:
        return preferred, best
    best_rgb = preferred
    seen = {preferred}
    for candidate in list(palette or []) + BUILTIN_PALETTE:
        rgb = _to_rgb(candidate)
        if rgb in seen:
            continue
        seen.add(rgb)
        s = score(background, mask, rgb)
        if s is None:
            continue
        if s >= min_contrast:
            return rgb, s
        if s > best:
            best, best_rgb = s, rgb
    return best_rgb, best


def _to_rgb(color):
    if isinstance(color, (tuple, list)):
        return tuple(color[:3])
    from style_file import parse_color
    return tuple(parse_color(color))


def text_on(fill_rgb, fg_rgb):
    """fg when it reaches TEXT_MIN_CONTRAST on fill, else black or white, whichever is clearer."""
    fg = tuple(fg_rgb[:3])
    if ratio(fg, fill_rgb) >= TEXT_MIN_CONTRAST:
        return fg
    return _BLACK if ratio(_BLACK, fill_rgb) >= ratio(_WHITE, fill_rgb) else _WHITE
