# Full page when the page scrolls inside a box

Many web apps scroll inside a box (a header, a sidebar, and a main area) instead of scrolling the document, so `fullPage=true` returns only the viewport. `references/full-page.md` detects that box and tells the agent to grow the browser window until nothing scrolls, then take a viewport screenshot. This recipe builds two such pages and follows that recipe in a real browser.

## Sub-features

- `scrollbox-detect` finds the main scroll box and lists the other scroll areas.
- `scrollbox-capture` follows the tall-window recipe on an app-shell page and measures the image.
- `scrollbox-annotate` annotates the tall image with coordinates measured in the tall state.
- `scrollbox-restore` puts the window back to the tutorial size.
- `scrollbox-body` does the same when `body` itself is the scroll box.

## How to get to it (user POV)

- Follow `skills/document-website/SKILL.md` step 2 (full-page screenshot) and `skills/document-website/references/full-page.md` on a page whose content scrolls inside a box.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`, with `SHOTS` from `setup`.
- The Playwright MCP tools (`browser_resize`, `browser_navigate`, `browser_evaluate`, `browser_take_screenshot`, `browser_wait_for`). Without them, report every bullet as skipped, naming the missing tools.
- `DETECT` below means the detection function copied from `references/full-page.md`.

- **Detect.** `browser_resize width=1280 height=720`, `browser_navigate url="about:blank"`. Run `"$PY" "$VDW" page --kind appshell` and pass its output to `browser_evaluate`; then run `DETECT`. Result: `documentScrolls` is `false`, `box.name` is `main#content`, `box.hidden` is `1376`, and `others` lists the sidebar with `hidden` `336`. After the window grows in the next bullet, a second `DETECT` reports `box` `null` and no entry in `others` with `hidden` above `0`.
- **Capture.** Follow the tall-window recipe: `browser_resize width=1280 height=2096` (720 + 1376), `browser_wait_for time=1`, `DETECT` again, then `browser_take_screenshot scale="css" filename="<$SHOTS>/appshell.png"`. Run `cp "$SHOTS/appshell.png" "$RUN/work/appshell.png"`. `"$PY" "$VDW" probe --image "$RUN/work/appshell.png" --at 0,0` is size `1280x2096`. `"$PY" "$VDW" find --image "$RUN/work/appshell.png" --color 0,160,0` has its bbox bottom at `y=2095`. `probe --at 300,10` is `(33, 47, 61)` and `--at 300,70` is `(220, 224, 230)`. `find --color 33,47,61 --region 0,100,1280,2096` is not found (the header appears once).
- **Annotate.** Still in the tall state, run `browser_evaluate function="() => { const r = document.querySelector('#last').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }"`, write `[{"type":"box","rect":[x-4, y-4, w+8, h+8]}]` to `$RUN/work/scrollbox-markers.json`, and run `"$PY" "$VDW" run --run "$RUN" --name scrollbox-annotate -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/appshell.png" --output "$RUN/evidence/appshell_annotated.png" --markers-file "$RUN/work/scrollbox-markers.json"`. Exit `0`. Two `[warn]` lines are expected: the box is cut off at the bottom edge (the green block touches the image bottom, so the box's lower side is outside), and the red box is swapped to black because red blends into the green block. `probe --at <x-3>,<y+h/2>` on the annotated image is a marker color (`(0, 0, 0)` after the swap). Read a crop of the image: the box surrounds the green block with no offset.
- **Restore.** `browser_resize width=1280 height=720`, then `browser_evaluate function="() => [innerWidth, innerHeight]"` is `[1280, 720]`.
- **Body.** At 1280x720, run `"$PY" "$VDW" page --kind bodyscroll` and pass its output to `browser_evaluate`, then `DETECT`: `documentScrolls` is `false`, `box.name` is `body`, `box.hidden` is `1280`. Follow the tall-window recipe: `browser_resize width=1280 height=2000`, `browser_wait_for time=1`, `DETECT` (box `null`), screenshot to `<$SHOTS>/body.png`, copy it to `$RUN/work/body.png`. The size is `1280x2000` and `find --color 0,160,0` has its bbox bottom at `y=1999`. Resize back to `1280x720`.
- **Proof.** Save the `DETECT` results and the probe and find outputs to `$RUN/evidence/scrollbox.txt`.

## Gotchas

- `fullPage=true` on these pages does not capture the hidden content: the app shell comes out `1280x720`, and the body layout can come out tall but with the bottom block missing. That is the failure this feature guards against.
- `DETECT` sets a `data-dw-scroll` attribute and scrolls the box to the top; it changes the page, which is intended.
- Replacing the document with `page --kind ...` drops any earlier page state; navigate to `about:blank` first when starting a bullet fresh.
- Screenshots must go to `$SHOTS` (the MCP refuses paths outside the repo), then be copied into `$RUN`.
