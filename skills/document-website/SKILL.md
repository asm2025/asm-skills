---
name: document-website
description: Creates customer-facing tutorial documentation for websites by taking annotated screenshots via Playwright MCP and compiling them into Word (.docx), HTML, or Markdown files. Use when asked to document a website, create a user guide, write a tutorial, or capture and annotate screenshots of a web application. Works with any URL (localhost or public). Supports arrows, numbered markers, highlight boxes, and text labels on screenshots.
---

## Overview

This skill guides the agent through a repeatable workflow for producing step-by-step tutorial documentation with annotated screenshots.

**Key capabilities**
- Capture viewport, full-page, or element screenshots via the Playwright MCP server
- Annotate screenshots with arrows, numbered circles, highlight boxes, and text labels using a bundled Python script
- Assemble the result into a `.docx`, `.md`, or self-contained `.html` file with a second bundled script

**Paths.** `<skill-dir>` below is the folder that contains this `SKILL.md` (Claude Code shows it as the skill's base directory). The scripts are in `<skill-dir>/scripts/`. Run them from the user's project folder, so relative output paths land in the project.

**Python.** Use `python3` on macOS and Linux, `python` on Windows.

## Workflow

### 1  Gather context
Before doing anything else, confirm:
- **Target URL** — read it from the conversation or task description; never guess.
- **Output format** — default is `.docx` (Word); use `.md` or `.html` if the user asks.
- **Sections / steps to document** — derive from the user's description or navigate the site to discover them.
- **Output directory** — default to `./docs/screenshots/` for images and `./docs/` for the final file.

Check the dependencies once (see Dependencies) before taking screenshots.

### 2  Take screenshots with Playwright MCP
Use the Playwright MCP tools (`browser_navigate`, `browser_resize`, `browser_snapshot`, `browser_take_screenshot`, `browser_click`, `browser_type`, `browser_evaluate`, etc.) available in the active session. Parameter names vary between `@playwright/mcp` releases, so check the tool schema the session lists before calling.

Set one viewport size before the first screenshot so every image in the tutorial has the same width:
```
browser_resize  width=1280  height=720
```

Always pass `filename` with an **absolute** path. A relative `filename` resolves against the MCP server's workspace root, which may not be the project folder, and without `filename` the tool saves `page-<timestamp>.png` to its own output directory.

**Viewport or full-page screenshot**
```
browser_navigate         url="<URL>"
browser_take_screenshot  filename="<project>/docs/screenshots/<step_name>.png"
browser_take_screenshot  filename="<project>/docs/screenshots/<step_name>_full.png"  fullPage=true
```

**Element screenshot**
To capture only one section, take an accessibility snapshot first, then screenshot that element by its reference. Current releases call the reference parameter `target` (older ones call it `ref`); pass `element`, a human-readable description of the element, alongside it.

```
browser_snapshot
browser_take_screenshot  element="Sign-up form"  target="<reference from snapshot>"  filename="<project>/docs/screenshots/<step_name>.png"
```

There is no clip-by-coordinates option. To capture a region that is not a single element, screenshot the viewport and place markers on the region instead. `fullPage` cannot be combined with an element screenshot.

Leave `scale` at its default (`css`), so one image pixel equals one CSS pixel and element positions from the page match image coordinates.

### 3  Find marker coordinates
Never guess coordinates from looking at a screenshot; markers land off target. Read them from the page:

- `browser_snapshot boxes=true` lists each element with `[box=x,y,width,height]` in CSS pixels relative to the viewport.
- Or run `browser_evaluate` with `() => { const r = document.querySelector('<selector>').getBoundingClientRect(); return [r.x, r.y, r.width, r.height, scrollX, scrollY]; }`.

Convert a box `x, y, w, h` to image pixels for the screenshot you took:

| Screenshot | Image x, y |
|---|---|
| Viewport | `x, y` |
| Full page | `x + scrollX, y + scrollY` (read the scroll offset in the same call) |
| Element | `x - ex, y - ey`, where `ex, ey` is the screenshotted element's box |

Then point markers at the box: an arrow `to` the box's left-middle `[x, y + h/2]` or center, a `box` with `rect` `[x - 4, y - 4, w + 8, h + 8]`, a `circle` just outside a corner.

### 4  Annotate screenshots
Write the markers to a JSON file and pass `--markers-file`. Inline `--markers` JSON also works in bash, but shell quoting breaks it easily, especially in PowerShell.

```bash
python3 <skill-dir>/scripts/annotate.py \
  --input  ./docs/screenshots/<step_name>.png \
  --output ./docs/screenshots/<step_name>_annotated.png \
  --markers-file ./docs/screenshots/<step_name>_markers.json
```

`<step_name>_markers.json`:
```json
[{"type": "box", "rect": [960, 40, 120, 32]}, {"type": "circle", "at": [960, 40], "label": "1"}]
```

See `references/annotation-spec.md` for every marker type and field.

- Exit code `2` means invalid markers or arguments; each problem is listed as `[error] marker <n> ...` and nothing is written. Fix and rerun.
- Read every `[warn]` line. A marker outside or cut off at the image edge usually means wrong coordinates (see step 3). A missing-font or right-to-left warning means some text will not render correctly.
- Open each annotated image and check that every marker points at the right element.

Use annotated images (the `_annotated.png` variants) in the final document.

### 5  Assemble the document
Write a `steps.json` file, then build. The output format follows the `--output` extension: `.docx`, `.md`, or `.html`.

```bash
python3 <skill-dir>/scripts/build_docx.py \
  --title "Tutorial Title" \
  --steps ./docs/steps.json \
  --output ./docs/tutorial.docx
```

`steps.json` format (UTF-8):
```json
[
  {
    "heading": "Step 1: Log in",
    "body": "Open the login page.\n\nEnter your email and password, then choose Sign in.",
    "image": "./docs/screenshots/login_annotated.png",
    "caption": "The login page"
  }
]
```

| Field | Required | Description |
|---|---|---|
| `heading` | — | Step heading; defaults to `Step <n>` when empty or missing |
| `body` | — | Text under the heading; a blank line (`\n\n`) starts a new paragraph, a single `\n` is a line break |
| `image` | — | Screenshot path, or a list of paths for several screenshots in one step |
| `caption` | — | Small italic line under the image(s) |

A relative `image` path is looked up from the current folder first, then from the folder that holds `steps.json`.

- **Word:** images keep their on-screen size, shrunk to fit 6 x 8 inches; small element screenshots are not enlarged. PNG and JPEG work; WebP does not.
- **Markdown:** images are linked by path relative to the `.md` file, so keep the screenshots next to it when sharing.
- **HTML:** one file with every image embedded, ready to share on its own.

Exit codes: `0` saved; `1` saved, but an image was missing or unreadable (each one becomes a red `[Image ...]` line in the document and an `[error]` line on stderr), or the file could not be written (for example, it is open in Word); `2` invalid `steps.json` or arguments, nothing written. On `1` or `2`, fix the cause and rebuild.

### 6  Quality check
- The build exited `0`, and no `[warn]` from annotation was left unexplained.
- Each step has a heading, body text, and at least one annotated screenshot.
- Every annotated image was opened and its markers point at the right elements.
- Heading numbering is consistent (`Step 1`, `Step 2`, ...).

## Dependencies

| Package | Purpose | Install |
|---|---|---|
| `python-docx` | Build `.docx` files | `pip install python-docx` |
| `Pillow` | Image annotation | `pip install Pillow` |
| `arabic-reshaper`, `python-bidi` | Optional: Arabic, Hebrew, and other right-to-left text in markers | `pip install arabic-reshaper python-bidi` |
| `@playwright/mcp` | Browser + screenshots | registered as MCP server |

Check with:
```bash
python3 -c "import docx, PIL; print('OK')"
```

## Reference Files
- `references/annotation-spec.md` — marker types, fields, coordinate system, fonts, errors
- `scripts/annotate.py` — annotation CLI
- `scripts/build_docx.py` — tutorial assembler CLI (`.docx`, `.md`, `.html`)
