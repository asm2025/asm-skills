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
- **Output file** — default to `./docs/tutorial.<ext>` in the project folder, unless the user names another path.
- **Screenshots folder** (`<shots>` below) — run this from the project folder and use the path it prints:
  ```bash
  python3 <skill-dir>/scripts/screenshot_dir.py
  ```
  It picks, in order: a folder the user named (pass it as `--dir <path>`, or set `DOCUMENT_WEBSITE_SCREENSHOTS`); `<temp>/screenshots` when the project has a temp folder (`!tmp`, `tmp`, `temp`, `.tmp`, or `.temp`); otherwise `screenshots/` in the project folder. It creates the folder and prints its absolute path. Add `--sub <name>` to keep one tutorial's screenshots apart. Raw screenshots, annotated images, marker files, and `steps.json` all go here; only the finished tutorial goes to the output file.

Check the Python dependencies once before taking screenshots (see Dependencies), so a missing package does not stop the run after the screenshots are taken.

### 2  Take screenshots with Playwright MCP
Use the Playwright MCP tools (`browser_navigate`, `browser_resize`, `browser_snapshot`, `browser_take_screenshot`, `browser_click`, `browser_type`, `browser_evaluate`, etc.) available in the active session. Parameter names vary between `@playwright/mcp` releases, so check the tool schema the session lists before calling.

Set one viewport size before the first screenshot so every image in the tutorial has the same width:
```
browser_resize  width=1280  height=720
```

Always pass `filename` as an absolute path in `<shots>`, and pass `scale="css"`:
- The Playwright MCP only writes inside its allowed roots (the project folder and the MCP's own output folder); a path elsewhere fails with "File access denied ... outside allowed roots". `screenshot_dir.py` warns when `<shots>` is outside the project.
- A relative `filename` resolves against the MCP server's workspace root, which may not be the folder you expect.
- Without `filename`, the tool saves `page-<timestamp>.png` to its own output folder.
- `scale="css"` (required by some releases) makes one image pixel equal one CSS pixel, so element positions from the page match image coordinates. Never use `scale="device"`.

The MCP also writes page snapshots (`.yml`) to its output folder, `<project>/.playwright-mcp/` unless the MCP server was started with `--output-dir`. Add that folder, and `<shots>` if it is not already in an ignored temp folder, to the project's `.gitignore`.

**Viewport screenshot**
```
browser_navigate         url="<URL>"
browser_take_screenshot  scale="css"  filename="<shots>/<step_name>.png"
```

**Full-page screenshot**
A full-page capture drops the page's scrollbar, which shifts centered content sideways. Hide the scrollbar first and measure (step 3) in that same state, then capture:
```
browser_evaluate         function="() => { document.documentElement.style.overflow = 'hidden'; scrollTo(0, 0); }"
browser_take_screenshot  scale="css"  fullPage=true  filename="<shots>/<step_name>_full.png"
browser_evaluate         function="() => { document.documentElement.style.overflow = ''; }"
```
Run the last line before interacting with the page again.

**Element screenshot**
To capture only one section, take an accessibility snapshot first, then screenshot that element by its reference. Current releases call the reference parameter `target` (older ones call it `ref`); pass `element`, a human-readable description of the element, alongside it.

```
browser_snapshot
browser_take_screenshot  scale="css"  element="Sign-up form"  target="<reference from snapshot>"  filename="<shots>/<step_name>.png"
```

There is no clip-by-coordinates option. To capture a region that is not a single element, screenshot the viewport and place markers on the region instead. `fullPage` cannot be combined with an element screenshot.

### 3  Find marker coordinates
Never guess coordinates from looking at a screenshot; markers land off target. Read them from the page, in the same scroll and scrollbar state as the screenshot:

- `browser_snapshot boxes=true` lists each element with `[box=x,y,width,height]` in CSS pixels relative to the viewport.
- Or run `browser_evaluate` with `() => { const r = document.querySelector('<selector>').getBoundingClientRect(); return [r.x, r.y, r.width, r.height, scrollX, scrollY]; }`.

Convert a box `x, y, w, h` to image pixels for the screenshot you took:

| Screenshot | Image x, y |
|---|---|
| Viewport | `x, y` |
| Full page | `x + scrollX, y + scrollY`, measured with the scrollbar hidden as in step 2 (after `scrollTo(0, 0)` the offset is 0) |
| Element | `x - ex, y - ey`, where `ex, ey` is the screenshotted element's box |

Then point markers at the box: an arrow `to` the box's left-middle `[x, y + h/2]` or center, a `box` with `rect` `[x - 4, y - 4, w + 8, h + 8]`, a `circle` just outside a corner.

### 4  Annotate screenshots
Write the markers to a JSON file and pass `--markers-file`. Inline `--markers` JSON also works in bash, but shell quoting breaks it easily, especially in PowerShell.

```bash
python3 <skill-dir>/scripts/annotate.py \
  --input  <shots>/<step_name>.png \
  --output <shots>/<step_name>_annotated.png \
  --markers-file <shots>/<step_name>_markers.json
```

`<step_name>_markers.json`:
```json
[{"type": "box", "rect": [960, 40, 120, 32]}, {"type": "circle", "at": [960, 40], "label": "1"}]
```

See `references/annotation-spec.md` for every marker type and field.

- Exit code `2` means invalid markers or arguments; each problem is listed as `[error] marker <n> ...` and nothing is written. Fix and rerun.
- Colors come from the marker, then `--color`/`--bg`/`--fg`, then `--style` (see `references/style-file.md`). A `[warn]` about a swapped color is expected, not a failure: auto-contrast changed a color that blended into the screenshot.
- Read every `[warn]` line. A marker outside or cut off at the image edge usually means wrong coordinates (see step 3). A missing-font or right-to-left warning means some text will not render correctly.
- Open each annotated image and check that every marker points at the right element.

Use annotated images (the `_annotated.png` variants) in the final document.

### 5  Assemble the document
Write `<shots>/steps.json`, then build. The output format follows the `--output` extension: `.docx`, `.md`, or `.html`.

```bash
python3 <skill-dir>/scripts/build_docx.py \
  --title "Tutorial Title" \
  --steps <shots>/steps.json \
  --output ./docs/tutorial.docx
```

`steps.json` format (UTF-8):
```json
[
  {
    "heading": "Step 1: Log in",
    "body": "Open the login page.\n\nEnter your email and password, then choose Sign in.",
    "image": "login_annotated.png",
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

Options for `build_docx.py`:

| Option | Description |
|---|---|
| `--template <file>` | A `.docx` or `.dotx` for `.docx` output. The body is cleared; styles, page setup, headers, and footers carry over. A style the template lacks (`Title`, `Heading 2`, `Caption`) is added with a basic look and a `[warn]`. Ignored with a warning for `.md` and `.html`. A missing or non-Word file exits `2`. |

A relative `image` path is looked up from the current folder first, then from the folder that holds `steps.json`, so plain file names work when both are in `<shots>`.

- **Word:** images keep their on-screen size, shrunk to fit 6 x 8 inches; small element screenshots are not enlarged. PNG and JPEG work; WebP does not.
- **Markdown:** images are copied into `<name>_images/` beside the `.md` file (replaced on each build) and linked from there, so the tutorial keeps working after `<shots>` is cleaned up. Share the `.md` together with that folder.
- **HTML:** one file with every image embedded, ready to share on its own.

Exit codes: `0` saved; `1` saved, but an image was missing or unreadable (each one becomes a red `[Image ...]` line in the document and an `[error]` line on stderr), or the file could not be written (for example, it is open in Word); `2` invalid `steps.json` or arguments, nothing written. On `1` or `2`, fix the cause and rebuild.

### 6  Quality check
- The build exited `0`, and no `[warn]` from annotation was left unexplained.
- Each step has a heading, body text, and at least one annotated screenshot.
- Every annotated image was opened and its markers point at the right elements.
- Heading numbering is consistent (`Step 1`, `Step 2`, ...).

## Dependencies

| Package | Purpose | Needed for |
|---|---|---|
| `Pillow` | Image annotation | Every run (`annotate.py`) |
| `python-docx` | Build Word files | `.docx` output only |
| `arabic-reshaper`, `python-bidi` | Arabic, Hebrew, and other right-to-left text in markers | Optional; `annotate.py` warns when right-to-left text needs them |
| `@playwright/mcp` | Browser and screenshots | MCP server; the `essential-skills` Claude Code plugin registers it |

The Python packages are listed in `<skill-dir>/requirements.txt`.

**Check** with the same interpreter that will run the scripts:
```bash
python3 -c "import PIL, docx; print('OK')"
```
Leave out `docx` when the output is `.md` or `.html`.

**If a package is missing**, tell the user which one and ask before installing it. Install with the same interpreter, so the packages land where the scripts look for them:
```bash
python3 -m pip install -r <skill-dir>/requirements.txt
```
If pip refuses with `externally-managed-environment`, do not pass `--break-system-packages`. Ask the user whether to install with `--user`, or create a virtual environment and run every script with its interpreter.

The scripts also check their own imports: `annotate.py` and a `.docx` build exit with `<package> is not installed. Run: pip install <package>`. Install it as above, then rerun the same command.

**If the Playwright MCP tools are missing** from the session, stop and tell the user to install the `essential-skills` plugin or register `@playwright/mcp` with their agent. Screenshots cannot be taken any other way.

## Reference Files
- `references/annotation-spec.md` — marker types, fields, coordinate system, fonts, errors
- `scripts/annotate.py` — annotation CLI
- `scripts/build_docx.py` — tutorial assembler CLI (`.docx`, `.md`, `.html`)
- `scripts/screenshot_dir.py` — picks and creates the screenshots folder
- `requirements.txt` — Python packages the scripts need
