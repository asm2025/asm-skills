# Style the tutorial from the style file and a CSS file

`build_docx.py --style <style.json>` reads the `document` section of the style file (fonts, sizes, colors, alignment, and page setup) and applies it to the matching Word styles: `Normal`, `Title`, `Heading 2`, and `Caption`. With a template, the style file wins for the keys it names and the template keeps the rest. For `.html`, the same keys become CSS added after the built-in stylesheet, and `--css <file>` adds more after that. `.md` ignores the style file.

## Sub-features

- `style-docx` applies the `document` section to a default `.docx`: style fonts, sizes, colors, title alignment, and page setup; the direct formatting the style file names is dropped so the style decides.
- `style-template` applies it inside a template: the style file wins for the keys it names, the template keeps the rest, and the page settings are ignored with a warning.
- `style-html` turns the keys into CSS after the built-in stylesheet, and `--css` lands after that.
- `style-caption-center` keeps captions centered without a template when the style file has a `caption` block with no `align`, and `caption.align` overrides it.
- `style-md` ignores the style file for `.md` output, without a warning.
- `style-doc-errors` rejects an invalid `document` value and a missing `--css` file: exit 2, nothing written.

## How to get to it (user POV)

- Run `build_docx.py --title "<title>" --steps <steps.json> --style <style.json> --output <file>`, optionally with `--template <file>` or `--css <file.css>`, as in `SKILL.md` step 5 and `references/style-file.md`.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`.
- The **Clean steps fixture** and **Templates** bullets of `build-template.md` have been run (`$RUN/work/clean/steps.json`, `$RUN/work/acme.docx`).
- `$RUN/evidence/style-err/` does not exist yet.
- Several bullets expect a non-zero exit. Do not use `set -e`.

- **Style file.** Run `printf '%s' '{"document":{"font":"Arial","font_size":12,"color":"#222222","title":{"color":"#0B3D91","align":"left"},"heading":{"size":16,"color":"#AA5500"},"caption":{"color":"#008000"},"page":{"size":"a4","margins_in":0.75}}}' > "$RUN/work/docstyle.json"`. The title and heading colors differ from the template's (`8B0000` and `0B3D91`) on purpose, so a dump shows which one won.
- **style-docx.** Run `"$PY" "$VDW" run --run "$RUN" --name style-docx -- "$PY" skills/document-website/scripts/build_docx.py --title "Styled Tutorial" --steps "$RUN/work/clean/steps.json" --style "$RUN/work/docstyle.json" --output "$RUN/evidence/style/plain.docx"`. Exit `0`, stderr empty. Then `"$PY" "$VDW" docx-dump --docx "$RUN/evidence/style/plain.docx" --out "$RUN/evidence/style-docx.dump.txt"`. The dump shows:
  - `style Normal: font=Arial size=12.0 color=222222`
  - `style Heading 2: ... size=16.0 color=AA5500`
  - `style Title: ... color=0B3D91 ... align=LEFT (0)`, and the title paragraph `style='Title' align=-` (no direct centering)
  - `style Caption: ... color=008000`, and caption paragraphs (`Main page`, `Two images`) with `color=None` (no run-level color)
  - `section: page 8.27x11.69in margins 0.75/0.75/0.75/0.75in`
- **style-template.** Same style with `--template "$RUN/work/acme.docx"`, `--name style-template`, output `$RUN/evidence/style/acme.docx`. Exit `0`. Stderr is exactly `[warn] style file page settings are ignored with --template`. The dump shows:
  - `style Heading 2: font=Georgia ... color=AA5500` (the style color beats the template's `0B3D91`; the font stays `Georgia` because the style file names none for headings)
  - `style Title: ... color=0B3D91` (not the template's `8B0000`)
  - `section: page 8.50x11.00in margins 0.50/0.50/0.50/0.50in`, and `header: 'ACME Header'`
- **style-html.** Run `"$PY" "$VDW" run --run "$RUN" --name style-html -- "$PY" skills/document-website/scripts/build_docx.py --title "Styled Tutorial" --steps "$RUN/work/clean/steps.json" --style "$RUN/work/docstyle.json" --output "$RUN/evidence/style/styled.html"`. Exit `0`. Then:
  - `grep -c 'font-family: Arial' "$RUN/evidence/style/styled.html"` prints `1` or more, and `grep -A3 '^h2 {' "$RUN/evidence/style/styled.html"` lists a rule with `color: #AA5500` and `font-size: 16pt`.
  - Run `printf 'h2 { color: rgb(1, 2, 3); }' > "$RUN/work/extra.css"` and build again with `--css "$RUN/work/extra.css"`, `--name style-html-css`, output `$RUN/evidence/style/styled-css.html`. Exit `0`. `grep -n 'AA5500\|rgb(1, 2, 3)' "$RUN/evidence/style/styled-css.html"` lists the `AA5500` line before the `rgb(1, 2, 3)` line (the `--css` rule comes later, so it wins).
  - Build `.docx` with `--css "$RUN/work/extra.css"` (`--name style-css-ignored`, output `$RUN/evidence/style/ignored.docx`): exit `0`, stderr `[warn] --css applies to .html output (and .pdf output built with Chrome); ignored for .docx`.
- **style-caption-center.** Run `printf '%s' '{"document":{"caption":{"color":"#008000"}}}' > "$RUN/work/capstyle.json"` and `printf '%s' '{"document":{"caption":{"align":"right"}}}' > "$RUN/work/capright.json"`. Build `$RUN/work/clean/steps.json` without a template once with each (`--name style-caption-center` and `--name style-caption-right`, outputs `$RUN/evidence/style/capc.docx` and `$RUN/evidence/style/capr.docx`). Exit `0` for both. The dumps (`docx-dump`) show `style Caption: ... align=CENTER (1)` for the first (the old centered look) and `style Caption: ... align=RIGHT (2)` for the second. With `--template "$RUN/work/acme.docx"` and `capstyle.json`, the Caption style shows `align=-` (the template decides).
- **style-md.** Build the same steps to `.md` twice, once with `--style "$RUN/work/docstyle.json"` (`--name style-md`, output `$RUN/evidence/style/with/t.md`) and once without (`--name style-md-none`, output `$RUN/evidence/style/without/t.md`). Both exit `0` with empty stderr. `diff "$RUN/evidence/style/with/t.md" "$RUN/evidence/style/without/t.md"` prints nothing.
- **style-doc-errors.** Run `printf '%s' '{"document":{"page":{"size":"legal"}}}' > "$RUN/work/badstyle.json"`, then build to `$RUN/evidence/style-err/out.docx` with `--style "$RUN/work/badstyle.json"` (`--name style-doc-err`). Exit `2`, stderr has `[error] style file <path>: document.page.size must be one of letter, a4, got "legal"` and `[error] Nothing was written.`, and `ls "$RUN/evidence/style-err"` fails. Then build to `$RUN/evidence/style-err/out.html` with `--css "$RUN/work/missing.css"` (`--name style-css-missing`): exit `2`, stderr `[error] --css file not found: <path>`, and `ls "$RUN/evidence/style-err"` still fails.
- **Proof.** `$RUN/evidence/style/` holds the outputs, with the `style-*.txt` records and `style-*.dump.txt` files beside them.

## Gotchas

- The dump reads each style's own properties. `font=None` means the style inherits its font; a template that sets a font shows it (`Georgia` in the template case).
- Without a template, the built-in direct formatting (title centered, caption italic gray 9 pt) stays for what the style file does not name. A `title.align` drops the direct centering, and any `caption` key drops the caption's direct formatting (the Caption style is then centered unless `caption.align` says otherwise). That is why the title paragraph shows `align=-` here and the captions show `color=None`.
- `vdw run` exits with the script's code, so under `set -e` an expected exit `2` stops the shell.
