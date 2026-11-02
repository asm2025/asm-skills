# Tutorial pipeline

The document-website workflow takes a screenshot of a web page, reads element positions from the page, annotates the screenshot at those positions, and assembles a tutorial from the annotated images. This recipe runs that chain end to end, with a real browser when the session has one.

## Sub-features

- `pipeline-screenshot` captures a real page as a PNG file at a fixed viewport size.
- `pipeline-coordinates` reads an element's box from the page and turns it into image coordinates.
- `pipeline-annotate` annotates that capture at the element's position.
- `pipeline-docx` builds a `.docx` whose step embeds the annotated capture.

## How to get to it (user POV)

- Follow `skills/document-website/SKILL.md` steps 2 to 5 for a URL: screenshot with the Playwright MCP, find coordinates, annotate, build.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`.
- For `pipeline-screenshot` and `pipeline-coordinates`: the Playwright MCP tools in this session (`browser_resize`, `browser_navigate`, `browser_snapshot`, `browser_take_screenshot`, `browser_evaluate`). Without them, use the fixture and report both as skipped, naming the missing tools. Browser tools that only return an image to the chat, with no file, do not count.

- **Screenshot.** With the Playwright MCP, follow `SKILL.md` step 2: `browser_resize width=1280 height=720`, `browser_navigate url="https://example.com"`, then `browser_take_screenshot filename="<absolute path of $RUN/work/shot.png>"`. Without it, run `"$PY" "$VDW" fixture --out "$RUN/work/shot.png"`. Then run `"$PY" "$VDW" probe --image "$RUN/work/shot.png" --at 0,0` and check the size is `1280x720`.
- **Coordinates.** With the Playwright MCP, follow `SKILL.md` step 3: `browser_evaluate function="() => { const r = document.querySelector('h1').getBoundingClientRect(); return [r.x, r.y, r.width, r.height, scrollX, scrollY]; }"` and record `x, y, w, h`. Without it, use the fixture's submit button, `x, y, w, h = 200, 380, 160, 44`.
- **Annotate.** Box the element and point at it. Write `[{"type":"box","rect":[x-4, y-4, w+8, h+8]},{"type":"arrow","to":[x, y+h/2]}]` with the numbers filled in to `$RUN/work/pipeline-markers.json` (for the fixture: `[{"type":"box","rect":[196,376,168,52]},{"type":"arrow","to":[200,402]}]`), then run `"$PY" "$VDW" run --run "$RUN" --name pipeline-annotate -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/shot.png" --output "$RUN/evidence/shot_annotated.png" --markers-file "$RUN/work/pipeline-markers.json"`. Exit `0`, stderr empty. `"$PY" "$VDW" probe --image "$RUN/evidence/shot_annotated.png" --at <x-3>,<y+h/2>` is `(229, 57, 53)` (the box's left border at the element's middle). Read the image: the box surrounds the element and the arrow points at its left edge.
- **Steps.** Run `printf '[{"heading":"Step 1: Find the element","body":"The highlighted element is where you start.","image":"%s","caption":"Annotated page"}]' "$RUN/evidence/shot_annotated.png" > "$RUN/work/pipeline-steps.json"`.
- **Build.** Run `"$PY" "$VDW" run --run "$RUN" --name pipeline-docx -- "$PY" skills/document-website/scripts/build_docx.py --title "Pipeline Tutorial" --steps "$RUN/work/pipeline-steps.json" --output "$RUN/evidence/pipeline.docx"`. Exit `0`.
- **Proof.** Run `"$PY" "$VDW" docx-dump --docx "$RUN/evidence/pipeline.docx" --out "$RUN/evidence/pipeline.dump.txt"`. The dump shows `Title` `Pipeline Tutorial`, `Heading 2` `Step 1: Find the element`, one `IMAGE width=6.00in`, the caption, `inline images: 1`, and no `Image not found`. Report whether the screenshot and coordinates came from a real page (with its URL) or the fixture.

## Gotchas

- `@playwright/mcp` parameter names change between releases (`target` in current releases, `ref` in older ones). If the session's tool schema differs from `SKILL.md` step 2, report it as a doc mismatch.
- A relative `filename` resolves against the MCP server's workspace root, not the shell's current directory. Pass an absolute path.
- Do not pass `scale: "device"`; on a high-DPI display, image pixels would no longer match CSS pixels and the markers would land off target.
- A real page's colors are unknown in advance, so this recipe probes only the box border, which is drawn in a known color.
