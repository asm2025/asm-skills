# Tutorial pipeline

The document-website workflow takes a screenshot of a web page, reads element positions from the page, annotates the screenshot at those positions, and assembles a tutorial from the annotated images. This recipe runs that chain end to end in a real browser, for both a viewport and a full-page screenshot.

## Sub-features

- `pipeline-screenshot` captures a real page as a PNG file at a fixed viewport size.
- `pipeline-coordinates` reads an element's box from the page and turns it into image coordinates.
- `pipeline-annotate` annotates that capture at the element's position.
- `pipeline-fullpage` does the same on a full-page screenshot, where the scrollbar must be hidden before measuring.
- `pipeline-docx` builds a `.docx` whose step embeds the annotated capture.

## How to get to it (user POV)

- Follow `skills/document-website/SKILL.md` steps 2 to 5 for a URL: screenshot with the Playwright MCP, find coordinates, annotate, build.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`, with `SHOTS` from `setup`.
- The Playwright MCP tools in this session (`browser_resize`, `browser_navigate`, `browser_evaluate`, `browser_take_screenshot`). Without them, use the fixture for the viewport bullets (`"$PY" "$VDW" fixture --out "$RUN/work/shot.png"`, element box `200, 380, 160, 44`), skip the full-page bullets, and report `pipeline-screenshot`, `pipeline-coordinates`, and `pipeline-fullpage` as skipped, naming the missing tools. Browser tools that only return an image to the chat, with no file, do not count.
- `https://example.com` is reachable. Its content changes over time; the recipe measures it instead of assuming positions.

- **Screenshot.** Follow `SKILL.md` step 2: `browser_resize width=1280 height=720`, `browser_navigate url="https://example.com"`, then `browser_take_screenshot scale="css" filename="<$SHOTS>/shot.png"` (expand `$SHOTS` to its real path). Run `cp "$SHOTS/shot.png" "$RUN/work/shot.png"` and `"$PY" "$VDW" probe --image "$RUN/work/shot.png" --at 0,0`: size `1280x720`.
- **Coordinates.** Follow `SKILL.md` step 3 for the first paragraph: `browser_evaluate function="() => { const r = document.querySelector('p').getBoundingClientRect(); return [r.x, r.y, r.width, r.height, scrollX, scrollY]; }"`. Record `x, y, w, h` rounded to whole pixels; `scrollX` and `scrollY` are `0`.
- **Annotate.** Write `[{"type":"box","rect":[x-4, y-4, w+8, h+8]},{"type":"arrow","to":[x, y+h/2]}]` with the numbers filled in to `$RUN/work/pipeline-markers.json`, then run `"$PY" "$VDW" run --run "$RUN" --name pipeline-annotate -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/shot.png" --output "$RUN/evidence/shot_annotated.png" --markers-file "$RUN/work/pipeline-markers.json"`. Exit `0`, stderr empty. `"$PY" "$VDW" probe --image "$RUN/evidence/shot_annotated.png" --at <x-3>,<y+h/2>` is `(229, 57, 53)`. Read the image: the box closely surrounds the paragraph text and the arrow tip touches its left edge.
- **Full-page screenshot.** Follow `SKILL.md` step 2, which points at `references/full-page.md`: run its detection function (expect `box` null, since example.com has no inner scroll box; `documentScrolls` is true when the page is taller than the window, so resize to 1280x300 first if it is false), then use its document recipe and measure in between: `browser_evaluate function="() => { document.documentElement.style.overflow = 'hidden'; scrollTo(0, 0); const a = [...document.querySelectorAll('a')].pop().getBoundingClientRect(); return [a.x, a.y, a.width, a.height, scrollX, scrollY]; }"` (the page's last link), then `browser_take_screenshot scale="css" fullPage=true filename="<$SHOTS>/full.png"`, then `browser_evaluate function="() => { document.documentElement.style.overflow = ''; }"`. Run `cp "$SHOTS/full.png" "$RUN/work/full.png"`; its width is `1280`.
- **Full-page annotate.** Box the link: write `[{"type":"box","rect":[x-4, y-4, w+8, h+8]}]` to `$RUN/work/full-markers.json` and run `"$PY" "$VDW" run --run "$RUN" --name pipeline-fullpage -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/full.png" --output "$RUN/evidence/full_annotated.png" --markers-file "$RUN/work/full-markers.json"`. Exit `0`, stderr empty. Then `"$PY" "$VDW" find --image "$RUN/work/full.png" --color 0,0,238 --tolerance 120 --region <x-20>,<y-20>,<x+w+20>,<y+h+20>` finds the link text, and its bbox lies inside the box `rect`. Read a crop of the image: the box surrounds the link with no sideways offset.
- **Steps.** Run `printf '[{"heading":"Step 1: Find the element","body":"The highlighted element is where you start.","image":"%s","caption":"Annotated page"}]' "$RUN/evidence/shot_annotated.png" > "$RUN/work/pipeline-steps.json"`.
- **Build.** Run `"$PY" "$VDW" run --run "$RUN" --name pipeline-docx -- "$PY" skills/document-website/scripts/build_docx.py --title "Pipeline Tutorial" --steps "$RUN/work/pipeline-steps.json" --output "$RUN/evidence/pipeline.docx"`. Exit `0`.
- **Proof.** Run `"$PY" "$VDW" docx-dump --docx "$RUN/evidence/pipeline.docx" --out "$RUN/evidence/pipeline.dump.txt"`. The dump shows `Title` `Pipeline Tutorial`, `Heading 2` `Step 1: Find the element`, one `IMAGE width=6.00in`, the caption, `inline images: 1`, and no `Image not found`. Save the measured boxes to `$RUN/evidence/pipeline-coordinates.txt`, and report the URL and whether each sub-feature ran in a real browser.

## Gotchas

- The Playwright MCP refuses to write outside the repo ("outside allowed roots"), so screenshots go to `$SHOTS`, a per-run subfolder of the folder `screenshot_dir.py` picks for the repo (`<repo>/screenshots/` unless the repo has a temp folder), and are copied into `$RUN`. `cleanup` deletes `$SHOTS`, and the screenshots folder too when nothing else is in it.
- Pass `scale="css"`; this MCP release requires it. With `scale="device"` on a high-DPI display, image pixels would no longer match CSS pixels.
- Without hiding the scrollbar, a full-page capture of a page taller than the viewport shifts centered content sideways by half the scrollbar width (about 8 px on Windows), and the image comes out 1265 px wide. That is the bug the full-page bullets guard against.
- A viewport screenshot of a page taller than the viewport includes the scrollbar. That is fine: viewport coordinates still match.
- `@playwright/mcp` parameter names change between releases (`target` in current releases, `ref` in older ones). If the session's tool schema differs from `SKILL.md` step 2, report it as a doc mismatch.
- `example.com` once had an `<h1>`; it no longer does. Measure an element that exists today rather than hard-coding a selector from memory.
