# Style file

One JSON file sets colors and sizes for the whole tutorial. Pass it with `--style style.json`. `annotate.py` reads the `markers` section; `build_docx.py` reads the `document` section and ignores `markers` without a warning. `annotate.py` likewise ignores `document`.

Keep the file in UTF-8 (a byte order mark is fine). Write it once and pass the same file to every run so all screenshots match.

## `markers` section

```json
{
  "markers": {
    "defaults": {"color": "#1565C0", "bg": "#1565C0", "fg": "#FFFFFF"},
    "circle":   {"radius": 14},
    "arrow":    {"width": 5},
    "auto_contrast": true,
    "min_contrast": 3.0,
    "palette": ["#1565C0", "#E53935", "#FDD835", "#000000", "#FFFFFF"]
  }
}
```

| Key | Type | Default | Meaning |
|---|---|---|---|
| `markers.defaults.color` | color | `#E53935` | Arrow and box color |
| `markers.defaults.bg` | color | `#E53935` | Circle and label fill |
| `markers.defaults.fg` | color | `#FFFFFF` | Circle and label text |
| `markers.arrow.color`, `.width`, `.auto_contrast` | color, number >= 1, true/false | `#E53935`, `4`, on | Arrow settings |
| `markers.circle.radius`, `.bg`, `.fg`, `.auto_contrast` | number >= 1, color, color, true/false | `18`, `#E53935`, `#FFFFFF`, on | Circle settings |
| `markers.box.color`, `.width`, `.radius`, `.auto_contrast` | color, number >= 1, number >= 0, true/false | `#E53935`, `3`, `6`, on | Box settings |
| `markers.label.bg`, `.fg`, `.font_size`, `.auto_contrast` | color, color, number >= 1, true/false | `#E53935`, `#FFFFFF`, `16`, on | Label settings |
| `markers.auto_contrast` | true/false | `true` | Contrast switch; `false` turns auto-contrast off for every marker |
| `markers.min_contrast` | number 1 to 21 | `3.0` | Lowest contrast ratio a marker color may have against the screenshot before it is swapped |
| `markers.palette` | list of colors | built-in palette | Replacement colors tried first when a color is swapped, before the built-in red, blue, yellow, black, white |

Numbers have upper limits: font sizes (`document.*.size`, `document.font_size`, `markers.label.font_size`) up to 1638, `width` and `radius` up to 10000, and page margins up to 20 inches; a larger value is an `[error]` like any invalid value.

Colors are any CSS color: `"#E53935"`, `"#F00"`, `"rgb(229, 57, 53)"`, or a name such as `"orange"`. A per-type block accepts only that type's fields; positions and text (`to`, `from`, `at`, `rect`, `label`, `text`) are never allowed.

## `document` section

```json
{
  "document": {
    "font": "Segoe UI",
    "font_size": 11,
    "color": "#1F2328",
    "title":   {"font": "Segoe UI Semibold", "size": 26, "color": "#0B3D91", "bold": true, "align": "center"},
    "heading": {"size": 16, "color": "#0B3D91", "bold": true},
    "caption": {"size": 9, "color": "#666666", "italic": true},
    "page":    {"size": "letter", "margins_in": 1.0}
  }
}
```

| Key | Type | Meaning |
|---|---|---|
| `document.font`, `.font_size`, `.color` | text, number > 0 and <= 1638, color | Body text (the Word `Normal` style; HTML `body`) |
| `document.title`, `.heading`, `.caption` | block | The title (`Title`, HTML `h1`), step headings (`Heading 2`, `h2`), and captions (`Caption`, `figcaption`) |
| `.font`, `.size`, `.color`, `.bold`, `.italic`, `.align` | text, number > 0 and <= 1638, color, true/false, true/false, `left`/`center`/`right` | Fields of a `title`, `heading`, or `caption` block |
| `document.page.size`, `.margins_in` | `letter` or `a4`, number from 0 to 20 | Page size and all four margins, in inches (Word only, and not with `--template`) |

Every key is optional; a key you leave out keeps the built-in look (or the template's). In Word the settings go on the styles, never on single paragraphs, so a change in Word's style gallery still works. For `.html` the same keys become CSS (point sizes in `pt`) after the built-in stylesheet, and `--css <file>` adds a stylesheet after that, so it wins. `.md` ignores the style file. The style file wins over a `--template` for the keys it names; the template keeps everything else. `page` settings are ignored with a `[warn]` when `--template` is given.

Run: `python <skill-dir>/scripts/build_docx.py --title "..." --steps steps.json --style style.json --output tutorial.docx`.

## Auto-contrast keys

`annotate.py` swaps a marker color that blends into the screenshot (see `annotation-spec.md`, "Auto-contrast"). `markers.auto_contrast` turns it off for the whole file, a per-type `auto_contrast` turns it off for one marker type, and `--no-auto-contrast` turns it off for one run. `markers.min_contrast` is the lowest contrast ratio (WCAG, 1 to 21) a color may have; raise it to be stricter. `markers.palette` lists the colors tried first, in order, before the built-in `#E53935`, `#1565C0`, `#FDD835`, `#000000`, `#FFFFFF`. Circle and label text always needs 3.0:1 on its own fill, whatever `min_contrast` says. Each swap prints a `[warn]`.

## Which value wins (`markers`)

For each field a marker leaves out, the first match wins:

1. the field on the marker itself;
2. the command line: `--color` (arrows and boxes), `--bg` and `--fg` (circles and labels);
3. the style file: the per-type block (for example `markers.circle.radius`), then `markers.defaults`;
4. the built-in default.

## Problems

- Missing file, invalid JSON, a top level that is not an object, or an invalid value (for example `"radius": "big"` or `"document": {"page": {"size": "legal"}}`): `[error]` naming the file and key, exit `2`, nothing written.
- A key the file does not support (a typo such as `"colour"`): `[warn] style file <path>: unknown key markers.circle.colour` (or `document.title.colour`); the key is ignored and the image is still saved.
