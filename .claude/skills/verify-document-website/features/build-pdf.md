# Build PDF tutorials

`build_docx.py --output <file>.pdf` builds the tutorial as a PDF through the first PDF engine it finds: Word on Windows, LibreOffice, or Chrome/Edge (`--pdf-engine auto|word|libreoffice|chrome` picks one). Word and LibreOffice convert a `.docx` built with the template and style file; Chrome prints the HTML build, so `--style` and `--css` apply and `--template` does not. With `--css` and no `--template`, `auto` tries Chrome first, because only Chrome uses CSS. No PDF engine is started unless the output ends in `.pdf`. No engine found exits `2`; a locked output exits `1` before any engine starts; an engine failure exits `1` and keeps the temp folder.

## Sub-features

- `pdf-chrome` builds a PDF with `--pdf-engine chrome`: three images and the title text.
- `pdf-word` builds inside the template with Word: the template header text is on the page.
- `pdf-libreoffice` does the same with LibreOffice.
- `pdf-auto` picks the first engine found in Word, LibreOffice, Chrome order.
- `pdf-auto-css` picks Chrome when `--css` is given without `--template`.
- `pdf-missing-engine` exits `2` for a requested engine that is not installed, listing what was searched, and creates no output folder.
- `pdf-locked` exits `1` for an output held open, starts no engine, and leaves no temp folder.
- `pdf-engine-fail` exits `1` when the engine fails, prints its stderr tail, and keeps the temp folder with the intermediate `.html`.
- `pdf-paths` works with spaces and non-ASCII letters in the output and template paths.
- `pdf-css-ignored` warns that `--css` is ignored when Word or LibreOffice is the engine.
- `pdf-not-asked` ignores `--pdf-engine` for a non-`.pdf` output with a warning and starts no Word.

## How to get to it (user POV)

- Run `build_docx.py --title "<title>" --steps <steps.json> --output <file>.pdf [--pdf-engine <name>] [--template <file>] [--style <file>] [--css <file>]`, as in `SKILL.md` steps 1 and 5. Only when the user asks for PDF.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`, and `$RUN/evidence/markers-defaults.png`: if it is missing, make it with the exact command from the **Defaults** bullet of `annotate-markers.md`: `"$PY" "$VDW" run --run "$RUN" --name markers-defaults -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/markers-defaults.png" --no-auto-contrast --markers '[{"type":"arrow","to":[640,200]},{"type":"circle","at":[320,150],"label":"1"},{"type":"box","rect":[100,400,300,60]},{"type":"label","at":[100,380],"text":"Click here"}]'` (it needs the baseline `page.png`).
- The **Clean steps fixture** and **Templates** bullets of `build-template.md` have been run (`$RUN/work/clean/steps.json` with three images, `$RUN/work/acme.docx`).
- `$RUN/evidence/pdf-none/` does not exist yet.
- Record which engines exist: `"$PY" -c "import sys; sys.path.insert(0,'skills/document-website/scripts'); import pdf_engines; print(pdf_engines.find_engines())" | tee "$RUN/evidence/pdf-engines.txt"`. Skip the bullet of every engine whose value is `None`, and report it as skipped, not as passed.
- Count Word and LibreOffice processes before: `tasklist | grep -i -c -E "winword|soffice"` (Windows). Check it again at the end; it must be unchanged.
- The temp root is `"$PY" -c "import tempfile; print(tempfile.gettempdir())"`; call it `$TMPROOT`. `ls -d "$TMPROOT"/document-website-pdf-* 2>/dev/null` lists the build temp folders; note what it lists now.
- Several bullets expect a non-zero exit. Do not use `set -e`.

- **CSS file.** Run `printf 'h2 { color: rgb(1, 2, 3); }' > "$RUN/work/extra.css"`.
- **pdf-chrome** (needs `chrome`). Run `"$PY" "$VDW" run --run "$RUN" --name pdf-chrome -- "$PY" skills/document-website/scripts/build_docx.py --title "PDF Tutorial" --steps "$RUN/work/clean/steps.json" --pdf-engine chrome --output "$RUN/evidence/pdf/chrome.pdf"`. Exit `0`, stdout `Saved: <path> (engine: chrome)`, stderr empty. Then `"$PY" "$VDW" pdf-info --pdf "$RUN/evidence/pdf/chrome.pdf" --out "$RUN/evidence/pdf-chrome.info.txt"` prints `pages=<n>=1 or more> images=3` and `text_has=PDF Tutorial`. No new `document-website-pdf-*` temp folder is left.
- **pdf-word** (needs `word`). Same build with `--pdf-engine word --template "$RUN/work/acme.docx"`, `--name pdf-word`, output `$RUN/evidence/pdf/word.pdf`. Exit `0`, `(engine: word)`, `pdf-info` shows `pages>=1`, `images=3`, and `text_has=` starting with `ACME Header`. Check `tasklist | grep -i winword` shows no leftover Word.
- **pdf-libreoffice** (needs `libreoffice`). Same as `pdf-word` with `--pdf-engine libreoffice`, `--name pdf-libreoffice`, output `$RUN/evidence/pdf/lo.pdf`, `(engine: libreoffice)`.
- **pdf-auto.** Same build with no `--pdf-engine` and no `--css`, `--name pdf-auto`, output `$RUN/evidence/pdf/auto.pdf`. Exit `0`; the engine in stdout is the first found in the order Word, LibreOffice, Chrome, per `pdf-engines.txt`. Skip when no engine is found (run `pdf-missing-engine` instead).
- **pdf-auto-css** (needs `chrome`). Build with `--css "$RUN/work/extra.css"` and no `--pdf-engine` or `--template`, `--name pdf-auto-css`, output `$RUN/evidence/pdf/autocss.pdf`. Exit `0` and `(engine: chrome)`, even when Word is installed, and stderr has no `--css ... ignored` warning.
- **pdf-missing-engine.** Pick an engine from `ENGINES` whose `find_engines()` value is `None` (if all three are installed, replace `find_engines` as in `pdf-engine-fail`, returning all `None`, with the same `sys.argv`). Run with `--pdf-engine <missing> --output "$RUN/evidence/pdf-none/out.pdf"`. Exit `2`, stderr `[error]` lines that name what was searched and how to get it, and `[error] Nothing was written.`. `ls "$RUN/evidence/pdf-none"` fails (the folder was not created).
- **pdf-locked.** Needs an existing output: `cp "$RUN/evidence/pdf/auto.pdf" "$RUN/work/locked.pdf"` (or `chrome.pdf`). Then `"$PY" "$VDW" run --run "$RUN" --name pdf-locked --lock "$RUN/work/locked.pdf" -- "$PY" skills/document-website/scripts/build_docx.py --title T --steps "$RUN/work/clean/steps.json" --output "$RUN/work/locked.pdf"`. Exit `1`, stderr has `close it and run again`, no `Traceback`. The Word and LibreOffice process counts are unchanged, and `ls -d "$TMPROOT"/document-website-pdf-*` lists the same folders as before.
- **pdf-engine-fail.** Write a stub: on Windows `printf '@echo engine broke 1>&2\r\n@exit /b 1\r\n' > "$RUN/work/fail-chrome.cmd"`; elsewhere `printf '#!/bin/sh\necho engine broke >&2\nexit 1\n' > "$RUN/work/fail-chrome.sh" && chmod +x "$RUN/work/fail-chrome.sh"`. Run `"$PY" "$VDW" run --run "$RUN" --name pdf-engine-fail -- "$PY" -c "import sys; sys.path.insert(0,'skills/document-website/scripts'); import pdf_engines, build_docx; stub = sys.argv[1]; pdf_engines.find_engines = lambda: {'word': None, 'libreoffice': None, 'chrome': stub}; sys.argv = ['build_docx.py', '--title', 'T', '--steps', sys.argv[2], '--pdf-engine', 'chrome', '--output', sys.argv[3]]; build_docx.main()" "<absolute stub path>" "$RUN/work/clean/steps.json" "$RUN/evidence/pdf/fail.pdf"`. Exit `1`; stderr has `engine broke` and a kept temp folder path; that folder exists and holds the `.html`; `$RUN/evidence/pdf/fail.pdf` does not exist. Remove the kept folder afterward, by the exact path stderr printed. The substitution works because `build_docx` calls `pdf_engines.find_engines()` through the module.
- **pdf-libreoffice-stub.** Proves the build runs the LibreOffice program that engine detection picked, without LibreOffice installed. Write `printf '@echo lo stub broke 1>&2
@exit /b 1
' > "$RUN/work/fail-lo.cmd"` (elsewhere a `#!/bin/sh` stub like the one above) and run the **pdf-engine-fail** command with `'libreoffice': stub` and the other two `None`, `--pdf-engine libreoffice`, the stub's absolute path, name `pdf-libreoffice-stub`, and output `$RUN/evidence/pdf/lofail.pdf`. Exit `1`; stderr `LibreOffice could not convert the document:`, `lo stub broke`, and a kept temp folder path (remove it afterward). This reports `pdf-libreoffice` as skipped but shows that `docx_to_pdf_libreoffice` takes the program from `find_engines()` through the build.
- **pdf-paths.** Run `mkdir -p "$RUN/work/my templates" && cp "$RUN/work/acme.docx" "$RUN/work/my templates/acmé.docx"`. Build with `--template "$RUN/work/my templates/acmé.docx"` and `--output "$RUN/evidence/pdf out/Tutorial é.pdf"`, no `--pdf-engine`, `--name pdf-paths`. Exit `0`, `Saved:` names the output, and `pdf-info` on it shows `pages>=1` and `images=3`. With Chrome as the only engine the template warns as ignored, which is expected.
- **pdf-css-ignored** (needs `word` or `libreoffice`). Build with `--pdf-engine <that engine> --css "$RUN/work/extra.css"` (`--name pdf-css-ignored`, output `$RUN/evidence/pdf/cssign.pdf`). Exit `0`, stderr `[warn] --css applies to .pdf output only with the chrome engine; ignored with <engine>`.
- **pdf-not-asked.** Count `tasklist | grep -i -c winword`, then build `.docx` with `--pdf-engine word` (`--name pdf-not-asked`, output `$RUN/evidence/pdf/notasked.docx`). Exit `0`, stderr `[warn] --pdf-engine applies to .pdf output; ignored`, and the Word process count is unchanged.
- **Proof.** `$RUN/evidence/` holds `pdf/*`, `pdf-engines.txt`, the `pdf-*.txt` records, and the `pdf-*.info.txt` files.

## Gotchas

- Chrome and Edge may already be running for the user; do not count or kill them. Count only `winword` and `soffice`.
- Chrome can exit `0` without writing a PDF; the build counts that as an engine failure.
- Word and LibreOffice hold a lock while converting; if a run was interrupted, check `tasklist` for a stray `WINWORD.EXE` or `soffice.bin` and end only the one this run started.
- `images=3` counts embedded images; Chrome and Word both keep the three screenshots as images.
- `vdw run` exits with the script's code, so under `set -e` an expected exit `1` or `2` stops the shell.
