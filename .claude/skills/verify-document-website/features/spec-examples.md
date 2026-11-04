# Documented examples

An agent using document-website copies marker JSON from `references/annotation-spec.md` and commands from `SKILL.md`. Every one of those examples must run as written and draw what the text says it draws, and the docs must describe the code.

## Sub-features

- `spec-schema-example` runs the four-marker array under "JSON schema".
- `spec-arrow-example` runs "Arrow pointing at a button".
- `spec-numbered-example` runs "Numbered step markers".
- `spec-field-example` runs "Highlight a form field", with the label clear of the box.
- `spec-skill-commands` runs the `SKILL.md` step 1, 4, and 5 commands with `<skill-dir>` and `<shots>` filled in, from a project folder outside the repo.
- `spec-types-match` checks that the marker types documented in the spec are the keys of `DRAWERS` in `annotate.py`, and that the `steps.json` fields in `SKILL.md` match what `build_docx.py` reads.
- `spec-help` checks that `--help` on both scripts lists the flags the docs use.
- `spec-style-markers` runs the `markers` JSON from `style-file.md` through `annotate.py --style`.
- `spec-style-document` runs the `document` JSON from `style-file.md` and its `Run:` line, to `.docx` and `.html`.
- `spec-describe` runs `describe_docx.py <file>` from `templates.md` on that build, and its missing-file error.
- `spec-signin-rule` runs the saved sign-in path rule from `SKILL.md` (Sign-in) and `browser-modes.md` in a throwaway git project.
- `spec-fullpage-js` parses every JavaScript example in `full-page.md`.
- `spec-docsync` runs the documentation sync checks: the default red only where intended, every `--help` option documented, no repo-root script paths in `SKILL.md`.

## How to get to it (user POV)

- Read `skills/document-website/references/annotation-spec.md` and use an example as the marker array.
- Read `skills/document-website/SKILL.md` steps 1, 4, and 5 and run the commands shown.
- Run `annotate.py --help` or `build_docx.py --help`.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`.
- Copy each example's JSON from the current spec file, not from this map. If the spec changed and the JSON below no longer matches, use the spec's JSON and record the difference.

- **Schema example.** Run `"$PY" "$VDW" run --run "$RUN" --name spec-schema-example -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/spec-schema.png" --no-auto-contrast --markers '[{"type":"arrow","to":[640,200]},{"type":"circle","at":[320,150],"label":"1"},{"type":"box","rect":[100,400,300,60]},{"type":"label","at":[100,380],"text":"Click here"}]'`. Exit `0`, stderr empty.
- **Arrow example.** Run `"$PY" "$VDW" run --run "$RUN" --name spec-arrow-example -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/spec-arrow.png" --markers '[{"type":"arrow","to":[980,54]}]'`. Exit `0`, stderr empty. Read the image: the arrow tip lands at (980,54) inside the dark header, coming from the upper left.
- **Numbered example.** Run `"$PY" "$VDW" run --run "$RUN" --name spec-numbered-example -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/spec-numbered.png" --markers '[{"type":"circle","at":[120,80],"label":"1"},{"type":"circle","at":[640,300],"label":"2"},{"type":"circle","at":[900,540],"label":"3"}]'`. Exit `0`. Then run `"$PY" "$VDW" probe --image "$RUN/evidence/spec-numbered.png" --at 135,80 --at 655,300 --at 915,540`: all three are `(229, 57, 53)`. Read the image: badges show `1`, `2`, `3`.
- **Field example.** Run `"$PY" "$VDW" run --run "$RUN" --name spec-field-example -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/spec-field.png" --markers '[{"type":"box","rect":[200,310,400,44]},{"type":"label","at":[200,280],"text":"Enter your email here"}]'`. Exit `0`. `"$PY" "$VDW" find --image "$RUN/evidence/spec-field.png" --color 229,57,53 --region 195,275,610,309` reports `bbox [200,280,374,307]`: its bottom edge, the fourth number, is less than `310`, so the label pill ends above the box. Read the image: the label sits just above the outlined field.
- **SKILL.md commands.** Act as a user project outside the repo, with `<skill-dir>` set to the repo's skill folder. Run:
  - `SKILL_DIR="$("$PY" -c 'import pathlib; print(pathlib.Path("skills/document-website").resolve().as_posix())')"; mkdir -p "$RUN/work/userproj"`
  - `SHOTS_U="$(cd "$RUN/work/userproj" && "$PY" -B "$SKILL_DIR/scripts/screenshot_dir.py" 2>"$RUN/evidence/spec-skill-shots.txt")"; echo "$SHOTS_U"` (step 1): it ends in `/userproj/screenshots`.
  - `cp "$RUN/work/page.png" "$SHOTS_U/login.png"` (stands in for the step 2 screenshot)
  - `printf '%s' '[{"type": "box", "rect": [960, 40, 120, 32]}, {"type": "circle", "at": [960, 40], "label": "1"}]' > "$SHOTS_U/login_markers.json"` (the step 4 example file)
  - `(cd "$RUN/work/userproj" && "$PY" -B "$SKILL_DIR/scripts/annotate.py" --input "$SHOTS_U/login.png" --output "$SHOTS_U/login_annotated.png" --markers-file "$SHOTS_U/login_markers.json") > "$RUN/evidence/spec-skill-annotate.txt" 2>&1; echo "exit $?" >> "$RUN/evidence/spec-skill-annotate.txt"`
  - `printf '%s' '[{"heading": "Step 1: Log in", "body": "Open the login page.\n\nEnter your email and password, then choose Sign in.", "image": "login_annotated.png", "caption": "The login page"}]' > "$SHOTS_U/steps.json"` (the step 5 example, with its plain file name)
  - `(cd "$RUN/work/userproj" && "$PY" -B "$SKILL_DIR/scripts/build_docx.py" --title "Tutorial Title" --steps "$SHOTS_U/steps.json" --output ./docs/tutorial.docx) > "$RUN/evidence/spec-skill-build.txt" 2>&1; echo "exit $?" >> "$RUN/evidence/spec-skill-build.txt"`

  Both evidence files end in `exit 0` with no `[warn]` or `[error]` (the plain image name resolves through the `steps.json` folder), and `"$PY" "$VDW" docx-dump --docx "$RUN/work/userproj/docs/tutorial.docx"` shows `Step 1: Log in`, two body paragraphs, one `IMAGE width=6.00in`, and caption `The login page`.
- **Types match.** Run `"$PY" -B -c "import sys; sys.path.insert(0, 'skills/document-website/scripts'); import annotate, build_docx; print(sorted(annotate.DRAWERS), build_docx.FIELDS)"` and `grep '^### ' skills/document-website/references/annotation-spec.md`. Both list exactly `arrow`, `box`, `circle`, `label`, and `FIELDS` is `('heading', 'body', 'image', 'caption')`, the same four rows as the `steps.json` table in `SKILL.md` step 5. Save both outputs to `$RUN/evidence/spec-types-match.txt`.
- **Help.** Run `"$PY" "$VDW" run --run "$RUN" --name spec-help-annotate -- "$PY" skills/document-website/scripts/annotate.py --help` and `"$PY" "$VDW" run --run "$RUN" --name spec-help-build -- "$PY" skills/document-website/scripts/build_docx.py --help`. Both exit `0`. The first lists `--input`, `--output`, `--markers`, `--markers-file`, `--font`, and the second lists `--title`, `--steps`, `--output`.
- **Style markers example.** Copy the `markers` JSON from `style-file.md` to `$RUN/work/userproj/style-markers.json` (`printf '%s' '{"markers":{"defaults":{"color":"#1565C0","bg":"#1565C0","fg":"#FFFFFF"},"circle":{"radius":14},"arrow":{"width":5},"auto_contrast":true,"min_contrast":3.0,"palette":["#1565C0","#E53935","#FDD835","#000000","#FFFFFF"]}}' > ...`). Run `"$PY" "$VDW" run --run "$RUN" --name spec-style-markers -- "$PY" skills/document-website/scripts/annotate.py --input "$RUN/work/page.png" --output "$RUN/evidence/spec-style-markers.png" --style "$RUN/work/userproj/style-markers.json" --markers '[{"type":"box","rect":[700,100,200,100]},{"type":"arrow","to":[900,500]},{"type":"circle","at":[320,150],"label":"1"}]'`. Exit `0`, stderr empty (no unknown-key warning). `probe --at 701,150 --at 334,150` is `(21, 101, 192)` twice (blue from `defaults`), and `find --color 21,101,192 --region 300,130,340,170` has bbox `[306,136,334,164]` (radius 14, not the default 18).
- **Style document example.** Copy the `document` JSON from `style-file.md` to `$RUN/work/userproj/style-doc.json`, copy `$RUN/work/clean/*.png` and `steps.json` into `$RUN/work/userproj/`, then run the doc's `Run:` line from that folder with the skill path filled in: `(cd "$RUN/work/userproj" && "$PY" -B "$SKILL_DIR/scripts/build_docx.py" --title "Doc Style" --steps steps.json --style style-doc.json --output tutorial-style.docx)`. Exit `0`, stderr empty. `docx-dump` shows `style Normal: font=Segoe UI size=11.0 color=1F2328`, `style Title: font=Segoe UI Semibold size=26.0 color=0B3D91 bold=True ... align=CENTER (1)`, `style Heading 2: ... size=16.0 color=0B3D91 bold=True`, `style Caption: ... size=9.0 color=666666 ... italic=True`, `section: page 8.50x11.00in margins 1.00/1.00/1.00/1.00in`. The same command with `--output tutorial-style.html` exits `0`, and the file has `font-family: "Segoe UI";`, `font-size: 26pt;`, `font-size: 16pt;`, and `color: #0B3D91;`.
- **Describe example.** Run `"$PY" "$VDW" run --run "$RUN" --name spec-describe-built -- "$PY" skills/document-website/scripts/describe_docx.py "$RUN/work/userproj/tutorial-style.docx"` (the `templates.md` command). Exit `0`; it lists `Title: font Segoe UI Semibold, 26 pt, color #0B3D91`, `Normal: font Segoe UI, 11 pt, color #1F2328`, `Heading 2: font Segoe UI, 16 pt, color #0B3D91`, `Caption: ... 9 pt, color #666666`, the outline `Doc Style` with `Open the page` and `Two images` under it, and `images: 3`: what the style file asked for. On `"$RUN/work/userproj/none.docx"` (`--name spec-describe-missing`) it exits `2` with `[error] file not found:`.
- **Sign-in rule.** Build a throwaway project: `S="$RUN/work/signproj"; mkdir -p "$S/!tmp" "$S/docs/images" && ( cd "$S" && git init -q && printf '\!tmp/\n' > .gitignore )`. `( cd "$S" && "$PY" -B "$D" )` (with `D` the `screenshot_dir.py` path as in `screenshot-dir.md`) prints a screenshots folder under `!tmp/`, so `<temp>` is `!tmp`. `( cd "$S" && mkdir -p '!tmp/auth' && git check-ignore -q '!tmp/auth/example.com.json'; echo $? )` prints `0`: save is allowed. The paths a wrong agent would derive print `1` (refuse): `docs/auth/example.com.json` (from `--dir docs/images`), `screenshots/../auth/example.com.json` (no temp folder). Quote every `!tmp` path.
- **Full-page JavaScript.** Run `"$PY" - <<'EOF'` with a script that reads `references/full-page.md`, takes the one fenced `js` block and each `function="..."` value, writes them to a temp `.js` file as strings, and runs `node` on `for (const s of srcs) new Function('return (' + s + ')')`. Prints `parsed 3`: all three parse. (Running them in a browser is `full-page-scroll-box.md`.)
- **Doc sync.** Run `grep -rn "#E53935" skills/document-website --include=*.md --include=*.py`: hits only in `annotation-spec.md` (field defaults, the precedence list, a sample warning), `style-file.md` (defaults table and examples), `annotate.py` (`DEFAULT_RED` and two error hints), `contrast.py` (`BUILTIN_PALETTE`), and `style_file.py` (`COLOR_HINT`). For each of `annotate.py` and `build_docx.py`, run `"$PY" -B skills/document-website/scripts/<script> --help | grep -o -E -- '--[a-z-]+' | sort -u` and `grep -c -e <option>` over `SKILL.md` and `references/*.md` for each option except `--help`: every count is at least `1`. `grep -n "skills/document-website/scripts" skills/document-website/SKILL.md` prints nothing.
- **Proof.** `$RUN/evidence/` holds the five `spec-*.png` images (`spec-schema`, `spec-arrow`, `spec-numbered`, `spec-field`, `spec-style-markers`), their run records, the `spec-style-*`, `spec-describe-*`, and `spec-style-doc.dump.txt` records, `spec-skill-annotate.txt`, `spec-skill-build.txt`, `spec-types-match.txt`, and both help records.

## Gotchas

- `SKILL.md` writes `python3` with `\` line continuations. On Windows, `python3` may open the Microsoft Store alias instead of a real interpreter. Use `"$PY"` and keep each command on one line when reproducing.
- `SKILL_DIR` is computed by Python, not `$(pwd)`: in Git Bash, `pwd` prints `/d/...`, which Windows Python reads as `C:\d\...`.
- The **SKILL.md commands** bullet runs outside the repo on purpose. Script paths that only work from the repo root (`skills/document-website/...`) are the bug it guards against.
- `spec-schema-example` passes `--no-auto-contrast`: its red box crosses the fixture's blue submit button, so auto-contrast would swap it and print a `[warn]`. The other examples run as written, with auto-contrast on, and still print nothing.
- The spec says Playwright screenshots are typically 1280 px wide. The fixture is 1280x720, so examples meant for taller screenshots are not exercised here.
