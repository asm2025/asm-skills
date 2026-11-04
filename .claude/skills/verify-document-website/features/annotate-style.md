# Annotate style file and color defaults

`annotate.py` fills marker fields a marker leaves out from command-line options (`--color`, `--bg`, `--fg`), then from a style file (`--style`, `markers` section), then from the built-in red and white. A broken style file gives one clear `[error]` or `[warn]` naming the file and key, never a traceback.

## Sub-features

- `style-cli` applies `--color` to markers that set no color, and leaves a marker's own color alone.
- `style-file` reads `markers.defaults` and per-type blocks from `--style`; the per-type block beats `defaults`.
- `style-precedence` makes a command-line color beat the style file.
- `style-errors` reports a missing style file, a top-level array, an invalid value, and (with a byte order mark) unknown keys, without a traceback.

## How to get to it (user POV)

- Run `annotate.py --input <png> --output <png> --markers <json> --color "#00FF00"`, as in `annotation-spec.md` "Defaults and style file".
- Run `annotate.py ... --style <style.json>`, as in `references/style-file.md`.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`: `$RUN/work/page.png` is the 1280x720 fixture.
- Every run passes `--no-auto-contrast`, so the expected pixels are the exact colors asked for.
- A `run` that is expected to exit non-zero makes `vdw run` exit non-zero too. Do not use `set -e` for this recipe.

- **CLI color.** Run `"$PY" "$VDW" run --run "$RUN" --name style-cli -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/style-cli.png" --no-auto-contrast --color "#00FF00" --markers '[{"type":"box","rect":[100,100,200,100]},{"type":"box","rect":[400,100,200,100],"color":"#0000FF"}]'`. Exit `0`. Then `"$PY" "$VDW" probe --image "$RUN/evidence/style-cli.png" --at 101,150 --at 401,150`. Expected `(0, 255, 0)` (the box with no color took `--color`), then `(0, 0, 255)` (the marker's own color won).
- **Style file.** Run `printf '%s' '{"markers":{"defaults":{"color":"#FF00FF","bg":"#FF00FF"},"circle":{"radius":30,"bg":"#00AAAA"}}}' > "$RUN/work/style.json"`, then `"$PY" "$VDW" run --run "$RUN" --name style-file -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/style-file.png" --no-auto-contrast --style "$RUN/work/style.json" --markers '[{"type":"box","rect":[100,100,200,100]},{"type":"circle","at":[700,500]}]'`. Exit `0`. Then `probe --at 101,150 --at 725,500`. Expected `(255, 0, 255)` (`defaults.color` on the box), then `(0, 170, 170)` (the circle reached radius 30, and its per-type `bg` beat `defaults.bg`).
- **Precedence.** Run the same command as `style-file` with `--color "#00FF00"` added, named `style-precedence`, output `$RUN/evidence/style-precedence.png`. Exit `0`. `probe --at 101,150` is `(0, 255, 0)`: the command line beat the style file.
- **Errors.** Run each, named as shown, with `--input "$RUN/work/page.png" --output "$RUN/evidence/style-err.png" --no-auto-contrast --markers '[]'` plus the `--style` value:
  - `style-err-missing`: `--style "$RUN/work/nope.json"`. Exit `2`, stderr `[error] --style file not found:`.
  - `style-err-array`: after `printf '%s' '[1]' > "$RUN/work/style-array.json"`, `--style "$RUN/work/style-array.json"`. Exit `2`, stderr `[error] style file ... must contain a JSON object`.
  - `style-err-value`: after `printf '%s' '{"markers":{"circle":{"radius":"big"}}}' > "$RUN/work/style-bad.json"`, `--style "$RUN/work/style-bad.json"`. Exit `2`, stderr `[error] style file ...: markers.circle.radius must be a number >= 1, got "big"` then `[error] Nothing was written.`; `ls "$RUN/evidence/style-err.png"` fails.
  - `style-err-warn`: after `printf '\xef\xbb\xbf{"markers":{"circle":{"colour":"#000"}},"extra":1}' > "$RUN/work/style-bom.json"`, `--style "$RUN/work/style-bom.json"`. Exit `0`, stderr has `[warn] style file ...: unknown key markers.circle.colour` and `[warn] style file ...: unknown key extra`; `style-err.png` now exists.
  - No record contains `Traceback`: `grep -l Traceback "$RUN"/evidence/style-*.txt` prints nothing.
- **Proof.** `$RUN/evidence/` holds the `style-*.txt` records and the `style-cli.png`, `style-file.png`, `style-precedence.png` outputs.

## Gotchas

- `--no-auto-contrast` is part of every command here; without it a later release may swap a color that lands on a similar background.
- Write the BOM file with `printf '\xef\xbb\xbf...'`; an editor or `echo` may drop or double the BOM.
- The `style-err.png` output is shared by the error runs on purpose: it must not exist after `style-err-value`, and exists after `style-err-warn`. Run them in the order listed.
