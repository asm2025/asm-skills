# Annotate auto-contrast

`annotate.py` checks each marker against the pixels around it and swaps a color that would blend into the screenshot: first to the style file's `palette`, then to the built-in palette (red, blue, yellow, black, white), keeping the first color that reaches the threshold (default 3.0:1) and printing a `[warn]` for every swap. Circle and label text is also checked against its own fill (minimum 3.0:1, fixed). `--no-auto-contrast`, `markers.auto_contrast: false`, and a marker's own `"auto_contrast": false` turn it off.

## Sub-features

- `contrast-default` swaps low-contrast colors on the four-strip fixture and warns for each swap, and only for those.
- `contrast-off` (`--no-auto-contrast`) leaves every color alone and prints no warnings.
- `contrast-marker-off` (`"auto_contrast": false` on one marker) leaves just that marker alone.
- `contrast-palette` tries the style file's `palette` before the built-in one.
- `contrast-threshold` (`markers.min_contrast`) lowers the bar so nothing is swapped.
- `contrast-offimage` skips markers that are off the image or cut off, quietly, and keeps the existing off-image warnings.
- `contrast-warn-once` prints a missing-font warning once, not once for the check and once for the real draw.
- `contrast-tall` stays fast on a very tall full-page image.

## How to get to it (user POV)

- Run `annotate.py` with no color options; auto-contrast is on by default.
- Add `--no-auto-contrast`, or put `auto_contrast`, `min_contrast`, or `palette` in the `markers` section of a `--style` file, or add `"auto_contrast": false` to a marker. See `annotation-spec.md` "Auto-contrast".

## Driving it with vdw

Preconditions:

- A fresh `RUN`. `"$PY" "$VDW" fixture --kind contrast --out "$RUN/work/contrast.png"` has written the 1280x720 image of four full-height strips: orange `(232,131,58)` at x 0-319, black `(0,0,0)` at 320-639, white `(255,255,255)` at 640-959, gray `(119,119,119)` at 960-1279.
- `printf '%s' '[{"type":"circle","at":[160,360],"label":"1"},{"type":"circle","at":[480,360],"label":"2"},{"type":"circle","at":[800,360],"label":"3"},{"type":"circle","at":[1120,360],"label":"4"},{"type":"box","rect":[1000,100,240,60]},{"type":"arrow","from":[40,600],"to":[260,600]}]' > "$RUN/work/cm.json"` has written the markers file (six markers: four circles, a box on gray, an arrow on orange).
- Do not use `set -e`: some runs are expected to exit non-zero or print warnings.
- Every command below is `"$PY" "$VDW" run --run "$RUN" --name <id> -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/contrast.png" --output "$RUN/evidence/<id>.png" --markers-file "$RUN/work/cm.json"` plus the extras listed. In `<id>.txt`, `[warn]` lines are in stderr.

- **Default.** Name `contrast-default`, no extras. Exit `0`. `probe --image "$RUN/evidence/contrast-default.png" --at 172,360 --at 492,360 --at 812,360 --at 1132,360 --at 1001,130 --at 120,600`. Expected `(0,0,0)` (orange circle became black), `(229,57,53)` (red kept on black), `(229,57,53)` (red kept on white), `(253,216,53)` (gray circle became yellow), `(253,216,53)` (box on gray became yellow), `(0,0,0)` (arrow on orange became black). Stderr has exactly five `[warn]` lines: marker 1 (`bg #E53935`, `drew #000000`), marker 4 (`bg`, `drew #FDD835`), marker 4 (`fg #FFFFFF`, `drew #000000`), marker 5 (`color`, `drew #FDD835`), marker 6 (`color`, `drew #000000`), and none for markers 2 and 3 (red keeps 4.97:1 on black and 4.23:1 on white, and white text on red is 4.23:1, above the 3.0 text minimum). `find --image "$RUN/evidence/contrast-default.png" --color 0,0,0 --region 1105,345,1135,375` finds the black "4"; `find --color 255,255,255 --region 150,350,170,370` finds the white "1" on black; `find --color 255,255,255 --region 470,350,490,370` finds the white "2" on red. Read the image: every marker stands out.
- **Off.** Name `contrast-off`, extra `--no-auto-contrast`. Exit `0`. `probe --at 172,360 --at 1132,360` is `(229,57,53)` twice; stderr is empty.
- **Marker off.** Write `cm-m1off.json` as the markers file with marker 1 changed to `{"type":"circle","at":[160,360],"label":"1","auto_contrast":false}` (use `sed 's/"label":"1"/"label":"1","auto_contrast":false/' "$RUN/work/cm.json" > "$RUN/work/cm-m1off.json"`), name `contrast-marker-off`, with `--markers-file "$RUN/work/cm-m1off.json"` in place of the default file. `probe --at 172,360` is `(229,57,53)`; stderr has no `marker 1` line; the other four warnings and probes are as in `contrast-default`.
- **Palette.** After `printf '%s' '{"markers":{"palette":["#FFFFFF"]}}' > "$RUN/work/style-palette.json"`, name `contrast-palette`, extra `--style "$RUN/work/style-palette.json"`. `probe --at 1132,360` is `(255,255,255)` (white ring on gray beats the built-in yellow because the style palette is tried first), and `find --color 0,0,0 --region 1105,345,1135,375` finds the black "4" (white text on a white fill is swapped to black).
- **Threshold.** After `printf '%s' '{"markers":{"min_contrast":1}}' > "$RUN/work/style-min1.json"`, name `contrast-threshold`, extra `--style "$RUN/work/style-min1.json"`. Exit `0`, stderr has no `[warn]`, `probe --at 172,360 --at 1132,360 --at 1001,130 --at 120,600` is `(229,57,53)` four times, and `find --color 255,255,255 --region 1105,345,1135,375` finds the white "4".
- **Style switches.** After `printf '%s' '{"markers":{"auto_contrast":false}}' > "$RUN/work/style-ac-off.json"`, name `contrast-style-off`, extra `--style "$RUN/work/style-ac-off.json"`: exit `0`, stderr empty, `probe --at 172,360` is `(229,57,53)`. After `printf '%s' '{"markers":{"circle":{"auto_contrast":false}}}' > "$RUN/work/style-ac-circle.json"`, name `contrast-style-circle-off`, extra `--style "$RUN/work/style-ac-circle.json"`: `probe --at 172,360` is `(229,57,53)` (circles left alone) and `--at 1001,130` is `(253,216,53)` (the box is still swapped); stderr has exactly the box and arrow warnings (markers 5 and 6).
- **Off-image.** Write `printf '%s' '[{"type":"circle","at":[1300,360],"label":"9"},{"type":"circle","at":[1280,360],"label":"8"}]' > "$RUN/work/cm-off.json"`, name `contrast-offimage`, with `--markers-file "$RUN/work/cm-off.json"`. Exit `0`; stderr has `marker 1 (circle) is entirely outside the` and `marker 2 (circle) is cut off at the edge of the` (marker 2 also gets the usual swap warnings for the gray strip, which is fine); no `Traceback`.
- **Warn once.** Write `printf '%s' '[{"type":"label","at":[700,300],"text":"Go \ud80c\udc00"}]' > "$RUN/work/cm-glyph.json"` (a JSON surrogate pair for U+13000, a glyph none of the candidate fonts has; if `doctor` shows a font that has it, record this bullet as not applicable), name `contrast-warn-once`, with `--markers-file "$RUN/work/cm-glyph.json"`. Stderr has exactly one `no available font has` line, not two.
- **Tall image.** `"$PY" "$VDW" fixture --kind contrast --size 1280x16000 --out "$RUN/work/contrast-tall.png"`. Write the markers file `cm-tall.json`: ten circles `{"type":"circle","at":[160,<1500*k+500>],"label":"<k>"}` for k = 0..9 plus `{"type":"box","rect":[1000,15000,240,60]}` (generate it with `"$PY" -c 'import json;print(json.dumps([{"type":"circle","at":[160,1500*k+500],"label":str(k)} for k in range(10)]+[{"type":"box","rect":[1000,15000,240,60]}]))' > "$RUN/work/cm-tall.json"`). Name `contrast-tall`, with `--input "$RUN/work/contrast-tall.png" --markers-file "$RUN/work/cm-tall.json"`, timed: `time` the `vdw run` call. Exit `0` and the run takes under 10 s. Record the time in the evidence.
- **Proof.** `$RUN/evidence/` holds the `contrast-*.txt` records and the `contrast-*.png` outputs; `grep -l Traceback "$RUN"/evidence/contrast-*.txt` prints nothing.

## Gotchas

- The expected warnings are part of the pass condition, not noise: count them.
- The verdicts come from the 20th percentile of the ring of pixels just outside each marker, not one pixel. On this fixture red measures 1.6:1 on orange, 1.1:1 on gray, 4.97:1 on black, and 4.23:1 on white. If a probe differs, read the warning's measured ratios before changing anything.
- Other recipes that mark the blue `(25,118,210)` buttons pass `--no-auto-contrast` when they test something other than color; red on that blue is under 3:1 and would be swapped.
- The fixture's strips are exact quarters, so `contrast.png` marker coordinates in this recipe stay put only at 1280x720.
- The glyph file uses a JSON \ud80c\udc00 escape on purpose, so no shell or editor can mangle the character.
