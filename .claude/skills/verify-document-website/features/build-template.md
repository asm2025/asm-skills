# Build inside a Word template

`build_docx.py --template <file.docx|file.dotx>` builds the tutorial inside a Word template: the template body is cleared, and its styles, page setup, headers, and footers carry over. With a template, the title and captions get no direct alignment or run formatting (their styles decide); images stay centered. Styles the template does not define (`Title`, `Heading 2`, `Caption`) are added with a basic look and one warning each. A bad template exits 2 with nothing written.

## Sub-features

- `template-docx` builds inside a `.docx` template: header, footer, page setup, and styles carry over, and the template body is gone.
- `template-dotx` does the same for a `.dotx` template.
- `template-missing-style` adds a missing `Heading 2` style with a basic look and one warning.
- `template-ignored` warns that `--template` is ignored for `.md` and `.html` output.
- `template-errors` rejects a missing path, a text file, a PDF renamed to `.docx`, and a zip with a malformed `word/document.xml`: exit 2, no output, no output folder, no traceback.
- `template-none` leaves output without `--template` unchanged.

## How to get to it (user POV)

- Run `build_docx.py --title "<title>" --steps <steps.json> --template <file> --output <file.docx>`, as in `SKILL.md` step 5.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`.
- `$RUN/evidence/markers-defaults.png` exists. If not, make it now with the exact command from the **Defaults** bullet of `annotate-markers.md`: `"$PY" "$VDW" run --run "$RUN" --name markers-defaults -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/markers-defaults.png" --no-auto-contrast --markers '[{"type":"arrow","to":[640,200]},{"type":"circle","at":[320,150],"label":"1"},{"type":"box","rect":[100,400,300,60]},{"type":"label","at":[100,380],"text":"Click here"}]'` (it needs the baseline `page.png`).
- `$RUN/evidence/tmpl-err/` does not exist yet.
- `template-none` reuses the `build-docx` recipe's **Project images**, **Write steps**, **Build**, and **Dump** bullets.
- Several bullets expect a non-zero exit. Do not use `set -e`.

- **Clean steps fixture.** Three distinct images, every one present, so a build exits `0`. Run `mkdir -p "$RUN/work/clean" && cp "$RUN/evidence/markers-defaults.png" "$RUN/work/clean/a.png" && "$PY" -c "from PIL import Image; import sys; d=sys.argv[1]; Image.new('RGB',(300,80),(25,118,210)).save(d+'/b.png'); Image.new('RGB',(400,200),(0,160,0)).save(d+'/c.png')" "$RUN/work/clean" && printf '%s' '[{"heading":"Open the page","body":"First paragraph.","image":"a.png","caption":"Main page"},{"heading":"Two images","body":"Second step.","image":["b.png","c.png"],"caption":"Two images"}]' > "$RUN/work/clean/steps.json"`.
- **Templates.** Run `"$PY" "$VDW" template --out "$RUN/work/acme.docx"`, then `"$PY" "$VDW" template --out "$RUN/work/acme.dotx" --dotx`, then `"$PY" "$VDW" template --out "$RUN/work/noheading2.docx" --no-heading2`.
- **template-docx.** Run `"$PY" "$VDW" run --run "$RUN" --name template-docx -- "$PY" skills/document-website/scripts/build_docx.py --title "Template Tutorial" --steps "$RUN/work/clean/steps.json" --template "$RUN/work/acme.docx" --output "$RUN/evidence/tmpl/acme.docx"`. Exit `0`, stderr empty. Then run `"$PY" "$VDW" docx-dump --docx "$RUN/evidence/tmpl/acme.docx" --out "$RUN/evidence/template-docx.dump.txt"`. The dump shows:
  - `section: page 8.50x11.00in margins 0.50/0.50/0.50/0.50in`, `header: 'ACME Header'`, `footer: 'ACME Footer'`, `tables: 0`
  - no `TEMPLATE BODY TEXT`
  - the title paragraph `style='Title' align=-` with text `Template Tutorial` (no direct centering)
  - step headings with `style='Heading 2'`, and `style Heading 2: font=Georgia size=... color=0B3D91`
  - captions (`Main page`, `Two images`) with `style='Caption'` and no run-level formatting (`italic=None size=None color=None`)
  - image paragraphs still `align=CENTER (1)`
  - `inline images: 3`
- **template-dotx.** Same as `template-docx` with `acme.dotx`, `--name template-dotx`, and output `$RUN/evidence/tmpl/acme-dotx.docx`. Exit `0`, stderr empty, and the dump has the same lines as `template-docx`.
- **template-missing-style.** Same build with `noheading2.docx`, `--name template-missing-style`, and output `$RUN/evidence/tmpl/noh2.docx`. Exit `0`, stderr exactly one line `[warn] template has no 'Heading 2' style; added a basic one`. The dump shows step headings with `style='Heading 2'` and `style Heading 2: font=None size=14.0 color=None bold=True ...`. The added style has outline level 1: `"$PY" -c "import sys,docx; st=docx.Document(sys.argv[1]).styles['Heading 2']; print(st.element.xpath('w:pPr/w:outlineLvl/@w:val'))" "$RUN/evidence/tmpl/noh2.docx"` prints `['1']`.
- **template-ignored.** Run `"$PY" "$VDW" run --run "$RUN" --name template-ignored -- "$PY" skills/document-website/scripts/build_docx.py --title T --steps "$RUN/work/clean/steps.json" --template "$RUN/work/acme.docx" --output "$RUN/evidence/tmpl/ignored.html"`. Exit `0`, stderr `[warn] --template applies to .docx and .pdf output; ignored for .html`, and the HTML is written.
- **template-errors.** Make the bad inputs: `printf 'not a word file' > "$RUN/work/notword.docx"` and `printf '%%PDF-1.4\nfake\n' > "$RUN/work/fake-pdf.docx"`. For each of `"$RUN/work/missing.dotx"`, `"$RUN/work/notword.docx"`, and `"$RUN/work/fake-pdf.docx"`, run `"$PY" "$VDW" run --run "$RUN" --name template-err-<missing|text|pdf> -- "$PY" skills/document-website/scripts/build_docx.py --title T --steps "$RUN/work/clean/steps.json" --template <path> --output "$RUN/evidence/tmpl-err/out.docx"`. Also make a copy of `acme.docx` whose `word/document.xml` is malformed XML: `"$PY" -c "import zipfile,sys; zi=zipfile.ZipFile(sys.argv[1]); zo=zipfile.ZipFile(sys.argv[2],'w'); [zo.writestr(n, b'<w:document><unclosed>' if n=='word/document.xml' else zi.read(n)) for n in zi.namelist()]; zo.close()" "$RUN/work/acme.docx" "$RUN/work/badxml.docx"`, and run it too (`template-err-xml`). Each exits `2`. Stderr is `[error] --template file not found: <path>` for the missing path, and `[error] --template is not a Word document (.docx or .dotx): <path>` for the other three, then `[error] Nothing was written.`. No `Traceback`. `ls "$RUN/evidence/tmpl-err"` fails (the folder was not created).
- **template-none.** Run the `build-docx` recipe's **Build** and **Dump** bullets. The dump's pre-existing lines match that recipe's expected list (`Title` centered, `Heading 2`, caption `italic=True size=9.0 color=666666`, `Normal style font size: 11.0`), with the `section`, `header`, `footer`, `tables`, and `style` lines appended after them. For the default document, `header: ''`, `footer: ''`, and `tables: 0`.
- **Proof.** `$RUN/evidence/` holds `tmpl/*`, the `template-*.txt` records, and the `template-*.dump.txt` files.

## Gotchas

- `.dotx` is the same package as `.docx` except for one content type; `vdw template --dotx` rewrites it. python-docx refuses a real `.dotx` on its own, so a pass here proves the skill's rewrite works.
- `style Heading 2: font=None` after `template-missing-style` is expected: the added style sets only size, bold, and the outline level.
- The built `.docx` is a normal document; open it in Word to see the real look. No converter is installed here, so the dump is the proof.
- `vdw run` exits with the script's code, so under `set -e` an expected exit `2` stops the shell.
