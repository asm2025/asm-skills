---
name: document-website
description: Creates customer-facing tutorial documentation for websites by taking annotated screenshots via Playwright MCP and compiling them into Word (.docx), HTML, or Markdown files. Use when asked to document a website, create a user guide, write a tutorial, or capture and annotate screenshots of a web application. Works with any URL (localhost or public). Supports arrows, numbered markers, and highlight overlays on screenshots.
---

## Overview

This skill guides the agent through a repeatable workflow for producing step-by-step tutorial documentation with annotated screenshots.

**Key capabilities**
- Capture full-page or element-level screenshots via the Playwright MCP server
- Annotate screenshots with arrows, numbered circles, and highlight boxes using a bundled Python script
- Assemble the result into a `.docx`, `.html`, or `.md` file

## Workflow

### 1  Gather context
Before doing anything else, confirm:
- **Target URL** — read it from the conversation or task description; never guess.
- **Output format** — default is `.docx` (Word); fallback to `.md` or `.html` if the user says so.
- **Sections / steps to document** — derive from the user's description or navigate the site to discover them.
- **Output directory** — default to `./docs/screenshots/` for images and `./docs/` for the final file.

### 2  Take screenshots with Playwright MCP
Use the Playwright MCP tools (`browser_navigate`, `browser_screenshot`, `browser_click`, `browser_type`, etc.) available in the active session.

**Full-page screenshot**
```
browser_navigate  url="<URL>"
browser_screenshot
```

**Element / partial screenshot**
To capture only a specific section, use `browser_screenshot` with a CSS selector or clip region.  
The `@playwright/mcp` tool accepts an optional `element` parameter (CSS selector) or `ref` (element handle from a previous `browser_snapshot`).

```
# Snapshot the DOM to get element refs
browser_snapshot
# Then screenshot a specific element ref
browser_screenshot  ref="<element_ref>"
```

Alternatively, clip by coordinates:
```
browser_screenshot  clip='{"x":0,"y":0,"width":1280,"height":400}'
```

Save screenshots to `./docs/screenshots/<step_name>.png`.

### 3  Annotate screenshots
After capturing, call the annotation script to add arrows, numbered markers, or highlight boxes.

```bash
python3 skills/document-website/scripts/annotate.py \
  --input  ./docs/screenshots/<step_name>.png \
  --output ./docs/screenshots/<step_name>_annotated.png \
  --markers '[{"type":"arrow","to":[x,y]},{"type":"circle","at":[x,y],"label":"1"}]'
```

See `scripts/annotate.py --help` and `references/annotation-spec.md` for the full marker spec.

Use annotated images (the `_annotated.png` variants) in the final document.

### 4  Assemble the document

**Word (.docx) — default**  
Use `python-docx` to build the document programmatically.  
See `scripts/build_docx.py` for the standard template.

```bash
python3 skills/document-website/scripts/build_docx.py \
  --title "Tutorial Title" \
  --steps steps.json \
  --output ./docs/tutorial.docx
```

`steps.json` format:
```json
[
  {
    "heading": "Step 1: Log in",
    "body": "Navigate to the login page and enter your credentials.",
    "image": "./docs/screenshots/login_annotated.png"
  }
]
```

**Markdown (.md)**  
Build a standard Markdown file with `![alt](path)` image links.

**HTML**  
Build a self-contained HTML file with base64-embedded images so it can be shared as a single file.

### 5  Quality check
- Confirm every screenshot file exists and is non-empty before embedding.
- Each step in the document must have: heading, body text, and at least one screenshot.
- Proofread heading numbering for consistency.

## Dependencies

| Package | Purpose | Install |
|---|---|---|
| `python-docx` | Build `.docx` files | `pip install python-docx` |
| `Pillow` | Image annotation | `pip install Pillow` |
| `@playwright/mcp` | Browser + screenshots | registered as MCP server |

Check with:
```bash
python3 -c "import docx, PIL; print('OK')"
```

## Reference Files
- `references/annotation-spec.md` — full marker type catalogue and coordinate system
- `scripts/annotate.py` — standalone annotation CLI
- `scripts/build_docx.py` — docx assembler CLI
