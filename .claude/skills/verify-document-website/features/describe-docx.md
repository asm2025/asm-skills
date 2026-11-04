# Describe a Word reference document

`describe_docx.py <file.docx|file.dotx>` prints what a Word document looks like, so the agent can match it: page size and margins per section, header and footer text, the paragraph styles in use with their resolved font, size, color, bold, and italic, an outline of the title and headings, and image and table counts. A missing or non-Word file exits 2 with a message and no traceback.

## Sub-features

- `describe-template` describes the `acme.docx` template: page setup, header, footer, one table, no images, and only `Normal` under `styles used:`.
- `describe-tutorial` describes a tutorial built inside that template with a style file: resolved heading and title styles, the outline, and three images.
- `describe-errors` rejects a PDF renamed to `.docx` and a missing path: exit 2, no traceback.

## How to get to it (user POV)

- Run `describe_docx.py <file>` on a reference document, as in `references/templates.md`.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`.
- The **Clean steps fixture** and **Templates** bullets of `build-template.md` have been run (`$RUN/work/clean/steps.json`, `$RUN/work/acme.docx`).
- The **Style file** bullet of `build-style.md` has been run (`$RUN/work/docstyle.json`).
- Several bullets expect a non-zero exit. Do not use `set -e`.

- **describe-template.** Run `"$PY" "$VDW" run --run "$RUN" --name describe-template -- "$PY" skills/document-website/scripts/describe_docx.py "$RUN/work/acme.docx"`. Exit `0`, stderr empty. Stdout has `page: 8.50 x 11.00 in, margins 0.50/0.50/0.50/0.50 in`, `header: ACME Header`, `footer: ACME Footer`, `tables: 1`, `images: 0`. Under `styles used:` the only line starts with `Normal:`; `Heading 2` is not listed, and nothing follows `outline:`.
- **describe-tutorial.** Build the tutorial: `"$PY" "$VDW" run --run "$RUN" --name describe-build -- "$PY" skills/document-website/scripts/build_docx.py --title "Styled Tutorial" --steps "$RUN/work/clean/steps.json" --template "$RUN/work/acme.docx" --style "$RUN/work/docstyle.json" --output "$RUN/evidence/describe/tutorial.docx"` (exit `0`, one page-settings warning). Then run `"$PY" "$VDW" run --run "$RUN" --name describe-tutorial -- "$PY" skills/document-website/scripts/describe_docx.py "$RUN/evidence/describe/tutorial.docx"`. Exit `0`. Stdout has `header: ACME Header`, a `Heading 2: font Georgia, 16 pt, color #AA5500` line, a `Title:` line containing `color #0B3D91`, `images: 3`. The outline is `Styled Tutorial` with `Open the page` and `Two images` indented under it.
- **describe-errors.** Run `printf '%%PDF-1.4\nfake\n' > "$RUN/work/ref-fake.docx"`. Run `describe_docx.py` on it (`--name describe-err-pdf`) and on `"$RUN/work/ref-missing.docx"` (`--name describe-err-missing`). Each exits `2`. Stderr is `[error] --template is not a Word document (.docx or .dotx): <path>` for the PDF, and `[error] --template file not found: <path>` for the missing path. No `Traceback`.
- **Proof.** The `describe-*.txt` records in `$RUN/evidence/`.

## Gotchas

- Paragraphs inside tables are not listed under `styles used:`; only body paragraphs are.
- The error text says `--template` because the script reuses the template loader.
- `vdw run` exits with the script's code, so under `set -e` an expected exit `2` stops the shell.
