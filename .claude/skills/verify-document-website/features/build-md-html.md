# Build Markdown and HTML tutorials

`build_docx.py` picks the output format from the `--output` extension. `.md` writes Markdown and copies its images into `<name>_images/` beside it, so it keeps working after the screenshots folder is cleaned up. `.html` writes one self-contained page with every image embedded as base64. Both use the same `steps.json`, validation, and exit codes as the Word output.

## Sub-features

- `md-structure` writes `# title`, `## heading` per step, body paragraphs with line breaks, image links, and an italic caption.
- `md-images` copies each image once into `<name>_images/` as `NN-<file name>`, links it relatively (wrapping paths with spaces in `<...>`), and replaces the folder on every build.
- `md-escape` stops `<` and `>` in text from being read as HTML, while keeping the author's Markdown.
- `html-structure` writes a complete page: title, `<h1>`, one `<section>` with `<h2>` per step, paragraphs, a `<figure>` with images and `<figcaption>`.
- `html-embedded` embeds every image as a `data:` URI, so the page works on its own.
- `html-escape` escapes text, so `<b>` in a body shows as text.
- `mdhtml-missing-image` writes a visible missing-image line, prints `[error] Image not found`, and exits 1.

## How to get to it (user POV)

- Run `build_docx.py --title "<title>" --steps <steps.json> --output <file.md>` or `--output <file.html>`, as in `SKILL.md` step 5.

## Driving it with vdw

Preconditions:

- `$RUN/work/proj/` from the **Project images** bullet of `build-docx.md` exists.
- Do not use `set -e`; the missing-image runs exit 1.

- **Write steps.** Run `printf '%s' '[{"heading":"Open <the> page","body":"Use **bold** here.\nNext line.\n\nShow <b>tags</b> as text.","image":"shots/main page.png","caption":"Main page"},{"heading":"Missing","image":"shots/missing.png"}]' > "$RUN/work/proj/steps-text.json"`.
- **Markdown.** Run `"$PY" "$VDW" run --run "$RUN" --name build-md -- "$PY" skills/document-website/scripts/build_docx.py --title "Demo <Tutorial>" --steps "$RUN/work/proj/steps-text.json" --output "$RUN/evidence/mdhtml/tutorial.md"`. Exit `1`, stderr `[error] Image not found: shots/missing.png`. Then `cat "$RUN/evidence/mdhtml/tutorial.md"` shows, in order:
  - `# Demo &lt;Tutorial&gt;` and `## Open &lt;the&gt; page`
  - `Use **bold** here.  ` (two trailing spaces) then `Next line.`, a blank line, then `Show &lt;b&gt;tags&lt;/b&gt; as text.`
  - `![Main page](<tutorial_images/01-main page.png>)`, a link into the copied images folder, in angle brackets because of the space
  - `*Main page*`
  - `## Missing` and `**[Image not found: shots/missing.png]**`
- **Markdown images copied.** Run `ls "$RUN/evidence/mdhtml/tutorial_images"`: exactly `01-main page.png`. Then `cmp "$RUN/evidence/mdhtml/tutorial_images/01-main page.png" "$RUN/work/proj/shots/main page.png"` prints nothing (identical copy).
- **HTML.** Run `"$PY" "$VDW" run --run "$RUN" --name build-html -- "$PY" skills/document-website/scripts/build_docx.py --title "Demo <Tutorial>" --steps "$RUN/work/proj/steps-text.json" --output "$RUN/evidence/mdhtml/tutorial.html"`. Exit `1`, same stderr. Then check the page:
  - `grep -c '<img src="data:image/png;base64,' "$RUN/evidence/mdhtml/tutorial.html"` prints `1`, and `grep -c 'src="shots\|src="\.\./' "$RUN/evidence/mdhtml/tutorial.html"` prints `0` (no file links).
  - `grep -o '<title>.*</title>\|<h1>.*</h1>\|<h2>.*</h2>\|<figcaption>.*</figcaption>\|<p class="missing">.*</p>' "$RUN/evidence/mdhtml/tutorial.html"` lists `<title>Demo &lt;Tutorial&gt;</title>`, `<h1>Demo &lt;Tutorial&gt;</h1>`, `<h2>Open &lt;the&gt; page</h2>`, `<figcaption>Main page</figcaption>`, `<h2>Missing</h2>`, `<p class="missing">[Image not found: shots/missing.png]</p>`.
  - `grep -c 'Show &lt;b&gt;tags&lt;/b&gt; as text' "$RUN/evidence/mdhtml/tutorial.html"` prints `1`.
- **Markdown rebuild.** Build again over the same file from steps that use one image twice. Run `printf '%s' '[{"heading":"A","image":"shots/small.png"},{"heading":"B","image":"shots/small.png"}]' > "$RUN/work/proj/steps-twice.json"` and `"$PY" "$VDW" run --run "$RUN" --name build-md-rebuild -- "$PY" skills/document-website/scripts/build_docx.py --title Twice --steps "$RUN/work/proj/steps-twice.json" --output "$RUN/evidence/mdhtml/tutorial.md"`. Exit `0`. `ls "$RUN/evidence/mdhtml/tutorial_images"` lists only `01-small.png` (the earlier `01-main page.png` is gone), and `grep -c '01-small.png' "$RUN/evidence/mdhtml/tutorial.md"` prints `2`.
- **Self-contained.** Move the page away from the images and confirm nothing breaks. Run `cp "$RUN/evidence/mdhtml/tutorial.html" "$RUN/work/moved.html"` and `"$PY" -c "import re,sys,base64,io; from PIL import Image; s=open(sys.argv[1],encoding='utf-8').read(); m=re.search(r'base64,([A-Za-z0-9+/=]+)',s); print(Image.open(io.BytesIO(base64.b64decode(m.group(1)))).size)" "$RUN/work/moved.html"`. It prints `(1280, 720)`.
- **Proof.** `$RUN/evidence/mdhtml/` holds `tutorial.md` and `tutorial.html`, plus the `build-md.txt` and `build-html.txt` records. If a browser tool is available, open `tutorial.html` and screenshot it into `$RUN/evidence/mdhtml/tutorial-html.png`.

## Gotchas

- Markdown keeps `**bold**` and other Markdown the author wrote; only `<`, `>`, and `&` are escaped. Do not expect `*` to be escaped.
- The `.md` needs its `<name>_images/` folder beside it; moving one without the other breaks the links, which is expected. The HTML has no such dependency.
- Because the images folder is replaced on every build, the **Markdown rebuild** bullet must run after the **Markdown** checks.
- Missing images exit 1 for every format. The file is still written, so check both the exit code and the content.
