# Annotate markers

`annotate.py` draws arrows, numbered circles, highlight boxes, and text labels onto a screenshot and saves a new PNG of the same size, leaving the input untouched. Text is centered, drawn in a font that has every character, and right-to-left scripts are shaped.

## Sub-features

- `markers-defaults` draws each of the four types with only its required fields, in the default red `#E53935`.
- `markers-custom` honors every optional field: arrow `from`/`color`/`width`, circle `radius`/`bg`/`fg`, box `color`/`width`/`radius`, label `bg`/`fg`/`font_size`.
- `markers-file` reads the marker array from `--markers-file` instead of `--markers`.
- `markers-colors` accepts CSS color names and short hex, not only `#RRGGBB`.
- `markers-arrow-flip` points an auto-tailed arrow's tail back into the image when the target is near the top or left edge.
- `markers-centered` centers circle text on the circle and label text inside its pill.
- `markers-utf8` reads a `--markers-file` as UTF-8 whatever the system locale.
- `markers-fonts` switches fonts per text so symbols and CJK draw as glyphs, not boxes.
- `markers-rtl` shapes and orders Arabic and Hebrew text.
- `markers-input-intact` leaves the input PNG unchanged.

## How to get to it (user POV)

- Run `annotate.py --input <png> --output <png> --markers-file <file.json>`, as in `SKILL.md` step 4.
- Run `annotate.py --input <png> --output <png> --markers '<json array>'`, as in `annotation-spec.md` "JSON schema".

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`: `$RUN/work/page.png` is the 1280x720 fixture.
- `doctor` reports `arialbd.ttf` for `'Click here'`, `seguisym.ttf` for `'✓'`, `msyhbd.ttc` for `'完成'`, and `fallback=arabic-reshaper + python-bidi`. These are the Windows fonts the expected numbers below were measured with. On another OS, the probes on marker shapes still hold, but text bboxes differ; check centering by the rule (within 1 px), not the exact bbox.

- **Defaults.** Draw one marker of each type. Run `"$PY" "$VDW" run --run "$RUN" --name markers-defaults -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/markers-defaults.png" --no-auto-contrast --markers '[{"type":"arrow","to":[640,200]},{"type":"circle","at":[320,150],"label":"1"},{"type":"box","rect":[100,400,300,60]},{"type":"label","at":[100,380],"text":"Click here"}]'`. Exit `0`, stdout `Saved: ...markers-defaults.png`, stderr empty.
- **Probe defaults.** Run `"$PY" "$VDW" probe --image "$RUN/evidence/markers-defaults.png" --at 619,179 --at 335,150 --at 101,430 --at 250,430 --at 103,388 --at 5,700 --at 641,201`. Expected, in order: arrow shaft `(229, 57, 53)`, circle edge `(229, 57, 53)`, box left border `(229, 57, 53)`, box interior `(245, 246, 248)`, label pill `(229, 57, 53)`, untouched corner `(245, 246, 248)`, just past the arrow tip `(245, 246, 248)` (the shaft does not poke through the head).
- **Look.** Read `$RUN/evidence/markers-defaults.png`. The arrow points down-right with its tip at (640,200), the red badge shows a white bold `1`, the box outlines (100,400)-(400,460), and bold `Click here` sits in a red pill at (100,380).
- **Centered.** Draw only the circle and label, so no other marker overlaps the pill. Run `"$PY" "$VDW" run --run "$RUN" --name markers-centered -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/markers-centered.png" --markers '[{"type":"circle","at":[320,150],"label":"1"},{"type":"label","at":[100,380],"text":"Click here"}]'`. Then run these three:
  - `"$PY" "$VDW" find --image "$RUN/evidence/markers-centered.png" --color 255,255,255 --tolerance 100 --region 308,138,333,163` finds the circle glyph, `center (319.0,149.0)`: within 1 px of the circle center (320,150).
  - `"$PY" "$VDW" find --image "$RUN/evidence/markers-centered.png" --color 229,57,53 --region 95,375,300,420` finds the pill, `bbox [100,380,188,404]`, `center (144.0,392.0)`.
  - `"$PY" "$VDW" find --image "$RUN/evidence/markers-centered.png" --color 255,255,255 --tolerance 100 --region 102,382,186,404` finds the label glyphs, `center (143.5,391.5)`: within 1 px of the pill center.
- **Custom fields.** Write the custom markers to a file, then run them. Run `printf '%s' '[{"type":"arrow","from":[900,600],"to":[1000,600],"color":"#1565C0","width":6},{"type":"circle","at":[1100,300],"label":"12","radius":30,"bg":"#000000","fg":"#FFFF00"},{"type":"box","rect":[700,450,200,100],"color":"#00AA00","width":8,"radius":0},{"type":"label","at":[700,650],"text":"Big","bg":"#6A1B9A","font_size":28}]' > "$RUN/work/custom.json"` and `"$PY" "$VDW" run --run "$RUN" --name markers-file -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/markers-custom.png" --no-auto-contrast --markers-file "$RUN/work/custom.json"`. Exit `0`, stderr empty.
- **Probe custom.** Run `"$PY" "$VDW" probe --image "$RUN/evidence/markers-custom.png" --at 950,600 --at 950,606 --at 1126,300 --at 1135,300 --at 706,500 --at 710,500 --at 702,665`. Expected, in order: arrow `(21, 101, 192)`, just outside the 6 px shaft `(245, 246, 248)`, circle edge inside radius 30 `(0, 0, 0)`, outside it `(245, 246, 248)`, inside the 8 px green border `(0, 170, 0)`, just past it `(245, 246, 248)`, label pill `(106, 27, 154)`. Read the image: the `12` is yellow on black.
- **Colors and arrow flip.** Run `"$PY" "$VDW" run --run "$RUN" --name markers-flip -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/markers-flip.png" --no-auto-contrast --markers '[{"type":"arrow","to":[20,20]},{"type":"box","rect":[600,600,100,50],"color":"orange","width":4},{"type":"circle","at":[900,200],"bg":"#0A0"}]'`. Exit `0`, stderr empty. `"$PY" "$VDW" probe --image "$RUN/evidence/markers-flip.png" --at 41,41 --at 601,625 --at 900,200` gives `(229, 57, 53)` (the tail runs down-right from the tip, inside the image), `(255, 165, 0)` (orange), `(0, 170, 0)` (short hex `#0A0`). Read the image: the arrow at top left points up-left at (20,20).
- **UTF-8 file.** Draw a non-ASCII label twice: from a file with UTF-8 mode forced off (as on Windows Python 3.14 and older), and inline. Run `printf '%s' '[{"type":"label","at":[100,500],"text":"Café naïve"}]' > "$RUN/work/utf8.json"`, then `"$PY" "$VDW" run --run "$RUN" --name markers-utf8-file -- "$PY" -X utf8=0 skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/markers-utf8-file.png" --markers-file "$RUN/work/utf8.json"` and `"$PY" "$VDW" run --run "$RUN" --name markers-utf8-inline -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/markers-utf8-inline.png" --markers '[{"type":"label","at":[100,500],"text":"Café naïve"}]'`. Both exit `0`, and `"$PY" "$VDW" diff --before "$RUN/evidence/markers-utf8-inline.png" --after "$RUN/evidence/markers-utf8-file.png"` reports `changed pixels 0`.
- **Fonts and right-to-left.** Run `printf '%s' '[{"type":"label","at":[100,100],"text":"Done ✓ 完成"},{"type":"label","at":[100,200],"text":"مرحبا بالعالم"},{"type":"label","at":[100,300],"text":"שלום עולם"},{"type":"circle","at":[400,120],"label":"١"}]' > "$RUN/work/text.json"` and `"$PY" "$VDW" run --run "$RUN" --name markers-text -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/markers-text.png" --markers-file "$RUN/work/text.json"`. Exit `0`, stderr empty (no missing-font or right-to-left warning). Read the image: `Done ✓ 完成` shows a check mark and two Chinese characters, not boxes; `مرحبا بالعالم` reads right to left with joined letters; `שלום עולם` reads right to left; the badge shows the Arabic-Indic digit one.
- **Input intact.** Regenerate a pristine fixture with `"$PY" "$VDW" fixture --out "$RUN/work/pristine.png"`, then run `"$PY" "$VDW" diff --before "$RUN/work/pristine.png" --after "$RUN/work/page.png"`. It reports `changed pixels 0`.
- **Proof.** `$RUN/evidence/` holds every `markers-*.png` and its `markers-*.txt` run record. Save the probe, find, and diff output to `$RUN/evidence/markers-checks.txt` (append each with `>>`).

## Gotchas

- Do not move the coordinates. Every expected RGB and bbox above depends on the exact JSON, and on the fixture's colors.
- Do not probe the circle's center: the label glyph covers it.
- `find` with `--tolerance 100` against white also matches the light page background. Keep its `--region` strictly inside the circle or pill, as above.
- `-X utf8=0` is how to reproduce a non-UTF-8 locale on Python 3.15+, which turns UTF-8 mode on by default. Without it, the UTF-8 check passes even on a script that does not set an encoding.
- The venv from `setup` has `arabic-reshaper` and `python-bidi`, so the right-to-left check takes the shaping path. The warning path (neither raqm nor the packages) is covered in `annotate-checks.md`.
- `markers-defaults`, `markers-file` (custom), and `markers-flip` pass `--no-auto-contrast`: they test the exact colors asked for and the default red, and auto-contrast would swap the red box that crosses the blue submit button, the green box, the orange box, and the green circle on the pale page. Auto-contrast itself is covered in `annotate-contrast.md`.
- Pixel probes cannot read text. The font and right-to-left results are proved by reading the image, so do that step every run.
