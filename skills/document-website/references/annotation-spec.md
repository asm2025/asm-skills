# Annotation Spec

## Contents
- Coordinate system
- Marker types
- Colors
- Defaults and style file
- Text and fonts
- JSON schema
- Errors and warnings
- Examples

## Coordinate system

All coordinates are in **pixels relative to the top-left corner** of the input image (0, 0).
Playwright screenshots taken with the default `scale: "css"` use CSS pixels, so a viewport screenshot is as wide as the viewport (typically 1280 px). Get positions from the page, not by eye: see `SKILL.md` step 3 for reading element boxes and converting them for full-page and element screenshots.

A marker that is entirely outside the image, or cut off at its edge, still draws (the visible part) but prints a `[warn]`. That almost always means a coordinate mistake.

## Marker types

### `arrow`
Draws a thick arrow pointing **to** a target coordinate.
When `from` is omitted, the tail sits up and to the left of the tip. If that would leave the image (a target near the top or left edge), the tail flips to the other side, so the arrow stays visible.

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"arrow"` | ✓ | |
| `to` | `[x, y]` | ✓ | Tip of the arrow |
| `from` | `[x, y]` | — | Tail; auto-computed if omitted. Must differ from `to` |
| `color` | color | — | Default `"#E53935"` (red) |
| `width` | int ≥ 1 | — | Line width in px; default `4`. The head scales with it |

---

### `circle`
Draws a filled numbered circle (badge) at a position. The label is centered in the circle.

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"circle"` | ✓ | |
| `at` | `[x, y]` | ✓ | Center of the circle |
| `label` | str | — | Text inside the circle (keep ≤ 2 chars); omit for a plain dot |
| `radius` | int ≥ 1 | — | Default `18`. The label's font size is 85% of it |
| `bg` | color | — | Fill color; default `"#E53935"` |
| `fg` | color | — | Text color; default `"#FFFFFF"` |

---

### `box`
Draws a rounded highlight rectangle around a region.

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"box"` | ✓ | |
| `rect` | `[x, y, w, h]` | ✓ | Top-left origin, width, height (both > 0) |
| `color` | color | — | Default `"#E53935"` |
| `width` | int ≥ 1 | — | Border width; default `3` |
| `radius` | int ≥ 0 | — | Corner radius; default `6` |

---

### `label`
Draws a text label on a colored background pill, with the text centered in the pill.

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"label"` | ✓ | |
| `at` | `[x, y]` | ✓ | Top-left of the pill |
| `text` | str | ✓ | Display text; must not be empty |
| `bg` | color | — | Default `"#E53935"` |
| `fg` | color | — | Default `"#FFFFFF"` |
| `font_size` | int ≥ 1 | — | Default `16` |

---

## Colors

Any CSS color Pillow understands: `"#E53935"`, `"#F00"`, `"rgb(229, 57, 53)"`, or a name such as `"orange"`. Colors are opaque.

## Defaults and style file

A field a marker leaves out is filled from the first of these that sets it:

1. the field on the marker itself;
2. command-line options: `--color` (arrows and boxes), `--bg` and `--fg` (circles and labels);
3. the style file's `markers` section (`--style style.json`): first the per-type block (`markers.circle.radius`), then `markers.defaults`;
4. the built-in defaults in the tables above (red `#E53935`, white text).

| Option | Meaning |
|---|---|
| `--style <file>` | Style file (JSON). Only its `markers` section is read here; the same file can also carry a `document` section for `build_docx.py` |
| `--color <color>` | Color for arrows and boxes that set none |
| `--bg <color>` | Fill for circles and labels that set none |
| `--fg <color>` | Text color for circles and labels that set none |
| `--no-auto-contrast` | Accepted now; never replace a marker color for low contrast on the screenshot |

A command-line color is not an override: a marker that sets its own `color`, `bg`, or `fg` keeps it. Per-type blocks accept any field that marker type accepts except positions and text (`to`, `from`, `at`, `rect`, `label`, `text`). Every key, type, and default is in `references/style-file.md`.

A bad `--color`, `--bg`, or `--fg` value, a missing or unreadable style file, or an invalid style value exits `2` and writes nothing. An unknown key in the style file prints a `[warn]` and is ignored.

## Text and fonts

- Text is drawn in a bold sans-serif font: Arial Bold on Windows and macOS, DejaVu Sans Bold or Liberation Sans Bold on Linux.
- For each text, the script picks the first installed font that has every character, so symbols (`✓`, `→`) and Chinese, Japanese, or Korean text switch to a font that covers them (Segoe UI Symbol, Microsoft YaHei, Yu Gothic, Malgun Gothic, PingFang, Noto Sans CJK; `fc-match` on Linux as a last resort).
- When no font has a character, it draws as a box and a `[warn]` names it. Pass `--font path/to/font.ttf` to use one font for all text.
- Arabic, Hebrew, and other right-to-left text needs either Pillow built with libraqm or `pip install arabic-reshaper python-bidi`. Without either, letters draw unjoined and left to right, and a `[warn]` says so.
- Emoji draw as single-color outlines when a symbol font has them (Segoe UI Symbol on Windows); color emoji are not supported.

## JSON schema

Pass markers as a JSON array, in a UTF-8 file (preferred) or inline:

```json
[
  { "type": "arrow", "to": [640, 200] },
  { "type": "circle", "at": [320, 150], "label": "1" },
  { "type": "box",    "rect": [100, 400, 300, 60] },
  { "type": "label",  "at": [100, 380], "text": "Click here" }
]
```

`--markers-file path/to/markers.json` reads the file (a UTF-8 byte order mark is fine). `--markers '<json>'` takes the array inline; shell quoting breaks it easily, especially in PowerShell.

## Errors and warnings

| Exit | Meaning |
|---|---|
| `0` | Saved. `[warn]` lines may still need attention |
| `1` | A file could not be read or written (input missing, not an image, output not writable) |
| `2` | Invalid JSON, arguments, style file, or markers. Every marker problem is listed as `[error] marker <n> (<type>): ...`; a style file problem names the file and key; nothing is written |

Warnings (`[warn]` on stderr, image still saved):
- unknown marker `type` (the marker is skipped)
- marker outside, or cut off at, the image edge
- a character no installed font has
- right-to-left text without shaping support
- an unknown key in the style file (the key is ignored)

## Examples

**Arrow pointing at a button**
```json
[{ "type": "arrow", "to": [980, 54] }]
```

**Numbered step markers**
```json
[
  { "type": "circle", "at": [120, 80],  "label": "1" },
  { "type": "circle", "at": [640, 300], "label": "2" },
  { "type": "circle", "at": [900, 540], "label": "3" }
]
```

**Highlight a form field**
```json
[
  { "type": "box",   "rect": [200, 310, 400, 44] },
  { "type": "label", "at":   [200, 280], "text": "Enter your email here" }
]
```
