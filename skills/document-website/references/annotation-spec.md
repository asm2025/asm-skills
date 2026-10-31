# Annotation Spec

## Contents
- Coordinate system
- Marker types
- JSON schema
- Examples

## Coordinate system

All coordinates are in **pixels relative to the top-left corner** of the input image (0, 0).  
Use the Playwright screenshot dimensions to reason about positions — typically 1280 × 720 or 1280 × 900.

## Marker types

### `arrow`
Draws a thick arrow pointing **to** a target coordinate.  
The arrow tail is automatically offset to avoid covering the target.

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"arrow"` | ✓ | |
| `to` | `[x, y]` | ✓ | Tip of the arrow |
| `from` | `[x, y]` | — | Tail; auto-computed if omitted |
| `color` | CSS hex | — | Default `"#E53935"` (red) |
| `width` | int | — | Line width in px; default `4` |

---

### `circle`
Draws a filled numbered circle (badge) at a position.

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"circle"` | ✓ | |
| `at` | `[x, y]` | ✓ | Centre of the circle |
| `label` | str | ✓ | Text inside the circle (keep ≤ 2 chars) |
| `radius` | int | — | Default `18` |
| `bg` | CSS hex | — | Fill colour; default `"#E53935"` |
| `fg` | CSS hex | — | Text colour; default `"#FFFFFF"` |

---

### `box`
Draws a rounded highlight rectangle around a region.

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"box"` | ✓ | |
| `rect` | `[x, y, w, h]` | ✓ | Top-left origin, width, height |
| `color` | CSS hex | — | Default `"#E53935"` |
| `width` | int | — | Border width; default `3` |
| `radius` | int | — | Corner radius; default `6` |

---

### `label`
Draws a text label with a coloured background pill.

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"label"` | ✓ | |
| `at` | `[x, y]` | ✓ | Top-left of the label |
| `text` | str | ✓ | Display text |
| `bg` | CSS hex | — | Default `"#E53935"` |
| `fg` | CSS hex | — | Default `"#FFFFFF"` |
| `font_size` | int | — | Default `16` |

---

## JSON schema

Pass markers as a JSON array string to `--markers`:

```json
[
  { "type": "arrow", "to": [640, 200] },
  { "type": "circle", "at": [320, 150], "label": "1" },
  { "type": "box",    "rect": [100, 400, 300, 60] },
  { "type": "label",  "at": [100, 380], "text": "Click here" }
]
```

Or write the array to a `.json` file and pass `--markers-file path/to/markers.json`.

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
  { "type": "label", "at":   [200, 290], "text": "Enter your email here" }
]
```
