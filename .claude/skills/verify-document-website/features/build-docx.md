# Build the Word tutorial

`build_docx.py` turns a UTF-8 `steps.json` array into a Word document: a centered title, one Heading 2 per step, body paragraphs, one or more centered screenshots at their on-screen size (shrunk to fit the page, never enlarged), and an optional italic gray caption. Missing or unreadable images become red placeholder lines and exit 1; invalid steps exit 2 and write nothing.

## Sub-features

- `docx-title` writes the `--title` as a centered `Title` paragraph.
- `docx-step` writes heading (`Heading 2`), body, centered image, and caption (italic, 9 pt, `666666`) in that order.
- `docx-paragraphs` splits `body` on blank lines into paragraphs and keeps single newlines as line breaks.
- `docx-images` accepts `image` as a list, sizes each image at 96 px per inch, and shrinks it to fit 6 x 8 inches.
- `docx-default-heading` uses `Step <n>` when `heading` is empty or missing.
- `docx-relative-images` finds a relative image path from the current folder, then from the folder holding `steps.json`.
- `docx-missing-image` writes `[Image not found: <path>]` in red `CC0000`, still saves, prints `[error] Image not found: <path>`, and exits 1.
- `docx-unreadable-image` does the same for an image Word cannot embed (WebP), with `[Image not readable: <path>]`.
- `docx-invalid-steps` lists every invalid step and field, exits 2, and writes nothing; unknown fields only warn.
- `docx-utf8` reads `steps.json` as UTF-8 (with or without a byte order mark) whatever the system locale.
- `docx-outdir` creates missing parent folders of `--output`.
- `docx-locked` reports an output file locked by another program (Word) without a traceback, and exits 1.

## How to get to it (user POV)

- Run `build_docx.py --title "<title>" --steps <steps.json> --output <file.docx>`, as in `SKILL.md` step 5.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`.
- `$RUN/evidence/markers-defaults.png` exists. If not, make it now with the exact command from the **Defaults** bullet of `annotate-markers.md`: `"$PY" "$VDW" run --run "$RUN" --name markers-defaults -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/markers-defaults.png" --no-auto-contrast --markers '[{"type":"arrow","to":[640,200]},{"type":"circle","at":[320,150],"label":"1"},{"type":"box","rect":[100,400,300,60]},{"type":"label","at":[100,380],"text":"Click here"}]'` (it needs the baseline `page.png`).
- `$RUN/evidence/docx/` does not exist yet, so the run proves `docx-outdir`.
- Several bullets expect a non-zero exit. Do not use `set -e`.

- **Project images.** Make a project folder whose steps file uses paths relative to itself. Run `mkdir -p "$RUN/work/proj/shots" && cp "$RUN/evidence/markers-defaults.png" "$RUN/work/proj/shots/main page.png" && "$PY" -c "from PIL import Image; import sys; d=sys.argv[1]; Image.new('RGB',(300,80),(25,118,210)).save(d+'/small.png'); Image.new('RGB',(1280,6000),(200,200,200)).save(d+'/tall.png'); Image.new('RGB',(100,100),(1,1,1)).save(d+'/pic.webp')" "$RUN/work/proj/shots"`.
- **Write steps.** Run `printf '%s' '[{"heading":"Open the café page ✓","body":"First paragraph.\nSecond line.\n\nSecond paragraph.","image":"shots/main page.png","caption":"Main page"},{"body":"Two images.","image":["shots/small.png","shots/tall.png"],"alt":"x"},{"heading":"Broken","image":["shots/missing.png","shots/pic.webp"]}]' > "$RUN/work/proj/steps.json"`.
- **Build.** Run with UTF-8 mode forced off (as on Windows Python 3.14 and older), from the repo root, so the relative image paths only resolve through the steps folder. Run `"$PY" "$VDW" run --run "$RUN" --name build-docx -- "$PY" -X utf8=0 skills/document-website/scripts/build_docx.py --title "Fixture Tutorial" --steps "$RUN/work/proj/steps.json" --output "$RUN/evidence/docx/tutorial.docx"`. Exit `1`. Stdout `Saved: ...tutorial.docx`. Stderr, in order: `[warn] step 2: ignoring unknown field(s) alt`, `[error] Image not found: shots/missing.png`, `[error] Image not readable (use PNG or JPEG): shots/pic.webp`.
- **Dump.** Run `"$PY" "$VDW" docx-dump --docx "$RUN/evidence/docx/tutorial.docx" --out "$RUN/evidence/build-docx.dump.txt"`. The dump shows, in order:
  - `[00] style='Title' align=CENTER (1)` with text `Fixture Tutorial`
  - `style='Heading 2'` with text `Open the café page ✓` (not `cafÃ©`)
  - `text='First paragraph.\nSecond line.'`, then a separate paragraph `text='Second paragraph.'`
  - `IMAGE width=6.00in` (1280 px is 13.3 in at 96 px/in, shrunk to 6 in)
  - `italic=True size=9.0 color=666666` with text `Main page`
  - `style='Heading 2'` with text `Step 2`, then `Two images.`
  - `IMAGE width=3.12in` (300 px at 96 px/in, not enlarged)
  - `IMAGE width=1.71in` (1280x6000 px, shrunk to 8 in tall)
  - `style='Heading 2'` with text `Broken`
  - `color=CC0000` with text `[Image not found: shots/missing.png]`
  - `color=CC0000` with text `[Image not readable: shots/pic.webp]`
  - `inline images: 3`
- **Invalid steps.** Run `printf '%s' '[{"heading":5,"image":7},"x"]' > "$RUN/work/bad.json"` and `"$PY" "$VDW" run --run "$RUN" --name build-docx-invalid -- "$PY" skills/document-website/scripts/build_docx.py --title T --steps "$RUN/work/bad.json" --output "$RUN/evidence/docx/invalid.docx"`. Exit `2`. Stderr: `[error] step 1: 'heading' must be a string`, `[error] step 1: 'image' must be a path or a list of paths`, `[error] step 2: must be an object, got "x"`, `[error] Nothing was written.` `ls "$RUN/evidence/docx/invalid.docx"` fails. Then `printf '{}' > "$RUN/work/obj.json"` with the same command on `obj.json` gives exit `2` and `must contain a JSON array of steps, got object`, and `--output "$RUN/work/x.txt"` gives exit `2` and `--output must end in .docx, .md, .html, .htm, .pdf`.
- **Clean build with BOM.** Prove that a build with every image present exits 0, and that a byte order mark is accepted. Run `printf '\xef\xbb\xbf[{"heading":"Only step","body":"All images present.","image":"%s"}]' "$RUN/evidence/markers-defaults.png" > "$RUN/work/steps-ok.json"` and `"$PY" "$VDW" run --run "$RUN" --name build-docx-ok -- "$PY" skills/document-website/scripts/build_docx.py --title "Clean Build" --steps "$RUN/work/steps-ok.json" --output "$RUN/evidence/docx/clean.docx"`. Exit `0`, stderr empty.
- **Locked output (Windows).** Hold the clean document open with a no-sharing lock, the way Word does, and build onto it. Run `"$PY" "$VDW" run --run "$RUN" --name build-docx-locked --lock "$RUN/evidence/docx/clean.docx" -- "$PY" skills/document-website/scripts/build_docx.py --title T --steps "$RUN/work/steps-ok.json" --output "$RUN/evidence/docx/clean.docx"`. Exit `1`, stderr `[error] cannot write ...clean.docx: permission denied. If it is open in Word or another program, close it and run again.`, and no `Traceback`.
- **Proof.** `$RUN/evidence/` holds `docx/tutorial.docx`, `docx/clean.docx`, the `build-docx*.txt` records, and `build-docx.dump.txt`.

## Gotchas

- `vdw run` exits with the script's code, so under `set -e` an expected exit `1` or `2` stops the shell.
- The **Build** bullet runs from the repo root on purpose: `shots/...` does not exist there, so the images resolve only through the steps-folder fallback. Running from `$RUN/work/proj` would pass without proving the fallback.
- The body font size is set on the shared `Normal` style (dump line `Normal style font size: 11.0`), so a run-level `size=None` on body text is expected.
- `-X utf8=0` reproduces a non-UTF-8 locale on Python 3.15+. Without it, the UTF-8 check passes even on a script that does not set an encoding.
- `run --lock` works only on Windows. On other systems, Word-style locks do not exist; record the locked-output bullet as not applicable.
- No converter is installed to render the `.docx` as an image. The dump is the proof. For a visual check, the user opens `$RUN/evidence/docx/tutorial.docx` in Word.
