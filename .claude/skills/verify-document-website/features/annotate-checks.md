# Annotation input checks

`annotate.py` refuses bad input with a clear message instead of a traceback, and warns about markers that are probably wrong. Invalid markers or JSON exit 2 and write nothing; file problems exit 1; suspicious but drawable markers save the image and print `[warn]` lines.

## Sub-features

- `checks-invalid-markers` lists every invalid marker by number and field, exits 2, and writes no output.
- `checks-invalid-json` reports bad JSON with its position, and suggests `--markers-file` for inline JSON.
- `checks-not-array` rejects a top-level value that is not an array.
- `checks-missing-input` reports a missing input image, or a missing markers file, without a traceback.
- `checks-unknown-type` warns, skips the marker, and still writes the output.
- `checks-bounds` warns when a marker is entirely outside the image or cut off at its edge.
- `checks-missing-glyph` warns when no font has a character, and `--font` overrides the font.
- `checks-rtl-unshaped` warns when right-to-left text cannot be shaped.
- `checks-output-dir` creates missing parent folders of `--output`.

## How to get to it (user POV)

- Run `annotate.py` as in `SKILL.md` step 4 with a mistake in the markers, paths, or coordinates.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`.
- A `run` that is expected to exit non-zero makes `vdw run` exit non-zero too. Do not use `set -e` for this recipe.

- **Invalid markers.** Run `"$PY" "$VDW" run --run "$RUN" --name checks-invalid-markers -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/checks-invalid.png" --markers '[{"type":"arrow"},{"type":"circle","at":[1,"x"]},{"type":"box","rect":[1,2,3]},{"type":"label","at":[1,1],"text":""},{"type":"arrow","to":[5,5],"color":"#ZZZ"},5]'`. Exit `2`. Stderr has one `[error]` line each for `marker 1 (arrow): missing field 'to'`, `marker 2 (circle): field 'at' must be [x, y] numbers`, `marker 3 (box): field 'rect' must be [x, y, width, height]`, `marker 4 (label): field 'text' is empty`, `marker 5 (arrow): field 'color' is not a color`, `marker 6: must be an object`, then `[error] Nothing was written.` `ls "$RUN/evidence/checks-invalid.png"` fails.
- **Invalid JSON.** Run `"$PY" "$VDW" run --run "$RUN" --name checks-invalid-json -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/work/x.png" --markers '[{type:arrow}]'`. Exit `2`, stderr `[error] --markers is not valid JSON: Expecting property name enclosed in double quotes: line 1 column 3` and the `--markers-file` hint.
- **Not an array.** Run `"$PY" "$VDW" run --run "$RUN" --name checks-not-array -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/work/x.png" --markers '{}'`. Exit `2`, stderr `[error] markers must be a JSON array, got dict`.
- **Missing files.** Run `"$PY" "$VDW" run --run "$RUN" --name checks-missing-input -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/nope.png" --output "$RUN/work/x.png" --markers '[]'`: exit `1`, stderr `[error] input image not found: ...nope.png`. Then `"$PY" "$VDW" run --run "$RUN" --name checks-missing-markers-file -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/work/x.png" --markers-file "$RUN/work/nope.json"`: exit `2`, stderr `[error] markers file not found: ...nope.json`. Neither prints a `Traceback`.
- **Warnings.** Run `"$PY" "$VDW" run --run "$RUN" --name checks-warnings -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/checks/warnings.png" --markers '[{"type":"star","at":[10,10]},{"type":"circle","at":[3000,100],"label":"9"},{"type":"label","at":[1250,700],"text":"edge"},{"type":"label","at":[100,100],"text":"\u0f00 ok"}]'`. Exit `0`, the `checks/` folder was created, and stderr has, in order:
  - `[warn] marker 1: unknown type 'star', skipped (known: arrow, circle, box, label)`
  - `[warn] marker 2 (circle) is entirely outside the 1280x720 image (covers 2982,82 to 3018,118).` plus the scroll-offset hint
  - `[warn] marker 3 (label) is cut off at the edge of the 1280x720 image`
  - `[warn] marker 4 (label): no available font has ༀ; it will draw as a box. Pass --font with a font that has it.`
- **Font override.** Run `"$PY" "$VDW" run --run "$RUN" --name checks-font -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/checks/font.png" --font C:/Windows/Fonts/arial.ttf --markers '[{"type":"label","at":[100,100],"text":"Done ✓"}]'`. Exit `0`, stderr `[warn] marker 1 (label): no available font has ✓` (the forced regular Arial lacks it). With `--font "$RUN/work/nope.ttf"`, exit is `2` and stderr is `[error] --font file not found`; with `--font "$RUN/work/custom.json"` (a file that is not a font), exit is `2` and stderr is `[error] --font is not a TrueType/OpenType font`.
- **Right-to-left without shaping.** Hide the shaping packages by running from the work folder with an empty `bidi` stub on the path: run `mkdir -p "$RUN/work/nobidi/bidi" && : > "$RUN/work/nobidi/bidi/__init__.py"`, then `PYTHONPATH="$RUN/work/nobidi" "$PY" "$VDW" run --run "$RUN" --name checks-rtl-unshaped -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/checks/rtl.png" --markers '[{"type":"label","at":[100,100],"text":"مرحبا"}]'`. Exit `0`, stderr `[warn] marker 1 (label): right-to-left text needs Pillow with libraqm, or `pip install arabic-reshaper python-bidi`; neither is available`.
- **Proof.** `$RUN/evidence/` holds the `checks-*.txt` records and `checks/warnings.png`, `checks/font.png`, `checks/rtl.png`.

## Gotchas

- The `checks-rtl-unshaped` stub only works because the stub `bidi` package has no `get_display`. If doctor reports `raqm=True`, Pillow shapes the text itself and no warning appears; record the check as not applicable.
- The `--font` path is Windows-specific. On other systems, pass any installed font without `✓`.
- `\u0f00` in the JSON is the Tibetan syllable ༀ, written as an escape so the shell does not mangle it. None of the Windows candidate fonts has it, which is why it warns. On a machine where a candidate font or `fc-match` covers Tibetan, pick another uncovered character. Do not use an emoji: Segoe UI Symbol draws many of them as outlines.
