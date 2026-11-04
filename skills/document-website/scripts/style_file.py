#!/usr/bin/env python3
"""
style_file.py - Read and validate the style file shared by annotate.py and build_docx.py.

The file is one JSON object with two optional sections: "markers" (read by
annotate.py) and "document" (read by build_docx.py). See references/style-file.md.

Files are read as UTF-8; a byte order mark is fine. A broken file raises
StyleError with a message that names the file, never a raw traceback.
"""

import json
import math

try:
    from PIL import ImageColor
except ImportError:
    raise SystemExit("Pillow is not installed. Run: pip install Pillow")


class StyleError(ValueError):
    pass


TOP_LEVEL_KEYS = ("markers", "document")

# Fields each section of "markers" accepts. Positions and text are never allowed.
MARKER_FIELDS = {
    "defaults": {"color", "bg", "fg"},
    "arrow":    {"color", "width", "auto_contrast"},
    "circle":   {"radius", "bg", "fg", "auto_contrast"},
    "box":      {"color", "width", "radius", "auto_contrast"},
    "label":    {"bg", "fg", "font_size", "auto_contrast"},
}

# Top-level keys of the "markers" section that are not marker types.
MARKER_OPTIONS = {"auto_contrast", "min_contrast", "palette"}

COLOR_FIELDS = {"color", "bg", "fg"}
# Integer fields and their minimums.
INT_MINIMUMS = {"width": 1, "radius": 1, "font_size": 1}
# Box corner radius may be 0.
BOX_RADIUS_MINIMUM = 0

COLOR_HINT = "a CSS color such as \"#E53935\" or \"orange\""


def parse_color(value) -> tuple:
    """Return (r, g, b) for any CSS color Pillow understands, else raise StyleError."""
    try:
        return ImageColor.getrgb(str(value))[:3]
    except ValueError:
        raise StyleError(f"not a color: {json.dumps(value)} (use {COLOR_HINT})")


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def load_style(path):
    """Return ({"markers": {...}, "document": {...}}, warnings) for a style file path.

    With path None, returns empty sections. Raises StyleError for a missing file,
    invalid JSON, or a top level that is not an object.
    """
    sections = {"markers": {}, "document": {}}
    warnings = []
    if not path:
        return sections, warnings
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise StyleError(f"--style file not found: {path}")
    except json.JSONDecodeError as e:
        raise StyleError(f"style file {path} is not valid JSON: {e}")
    except UnicodeDecodeError as e:
        raise StyleError(f"style file {path} is not valid UTF-8 text: {e}")
    except OSError as e:
        raise StyleError(f"--style file could not be read: {path}: {e}")
    if not isinstance(data, dict):
        raise StyleError(f"style file {path} must contain a JSON object, "
                         f"got {type(data).__name__}")
    for key, value in data.items():
        if key in TOP_LEVEL_KEYS:
            sections[key] = value
        else:
            warnings.append(f"style file {path}: unknown key {key}")
    return sections, warnings


def _check_field(prefix: str, field: str, value, mtype: str, source: str) -> list:
    """Return error strings for one field value (empty when valid)."""
    where = f"style file {source}: {prefix}.{field}"
    if field in COLOR_FIELDS:
        try:
            parse_color(value)
        except StyleError:
            return [f"{where} must be {COLOR_HINT}, got {json.dumps(value)}"]
        return []
    if field == "auto_contrast":
        if not isinstance(value, bool):
            return [f"{where} must be true or false, got {json.dumps(value)}"]
        return []
    if field in INT_MINIMUMS:
        minimum = BOX_RADIUS_MINIMUM if (field == "radius" and mtype == "box") else INT_MINIMUMS[field]
        if not _num(value) or value < minimum:
            return [f"{where} must be a number >= {minimum}, got {json.dumps(value)}"]
    return []


def validate_markers(section, source: str):
    """Check a "markers" section; return (errors, warnings) as lists of text lines."""
    errors, warnings = [], []
    if not isinstance(section, dict):
        return [f"style file {source}: markers must be an object, "
                f"got {json.dumps(section)}"], warnings
    for key, value in section.items():
        if key in MARKER_FIELDS:
            if not isinstance(value, dict):
                errors.append(f"style file {source}: markers.{key} must be an object, "
                              f"got {json.dumps(value)}")
                continue
            for field, fvalue in value.items():
                if field not in MARKER_FIELDS[key]:
                    warnings.append(f"style file {source}: unknown key markers.{key}.{field}")
                    continue
                errors.extend(_check_field(f"markers.{key}", field, fvalue, key, source))
        elif key == "auto_contrast":
            if not isinstance(value, bool):
                errors.append(f"style file {source}: markers.auto_contrast must be true "
                              f"or false, got {json.dumps(value)}")
        elif key == "min_contrast":
            if not _num(value) or not 1 <= value <= 21:
                errors.append(f"style file {source}: markers.min_contrast must be a number "
                              f"from 1 to 21, got {json.dumps(value)}")
        elif key == "palette":
            if not isinstance(value, list) or not value:
                errors.append(f"style file {source}: markers.palette must be a list of "
                              f"colors, got {json.dumps(value)}")
            else:
                for i, item in enumerate(value):
                    try:
                        parse_color(item)
                    except StyleError:
                        errors.append(f"style file {source}: markers.palette[{i}] must be "
                                      f"{COLOR_HINT}, got {json.dumps(item)}")
        else:
            warnings.append(f"style file {source}: unknown key markers.{key}")
    return errors, warnings
