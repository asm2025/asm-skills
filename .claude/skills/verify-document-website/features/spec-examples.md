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
- **Proof.** `$RUN/evidence/` holds the four `spec-*.png` images, their run records, `spec-skill-annotate.txt`, `spec-skill-build.txt`, `spec-types-match.txt`, and both help records.

## Gotchas

- `SKILL.md` writes `python3` with `\` line continuations. On Windows, `python3` may open the Microsoft Store alias instead of a real interpreter. Use `"$PY"` and keep each command on one line when reproducing.
- `SKILL_DIR` is computed by Python, not `$(pwd)`: in Git Bash, `pwd` prints `/d/...`, which Windows Python reads as `C:\d\...`.
- The **SKILL.md commands** bullet runs outside the repo on purpose. Script paths that only work from the repo root (`skills/document-website/...`) are the bug it guards against.
- `spec-schema-example` passes `--no-auto-contrast`: its red box crosses the fixture's blue submit button, so auto-contrast would swap it and print a `[warn]`. The other examples run as written, with auto-contrast on, and still print nothing.
- The spec says Playwright screenshots are typically 1280 px wide. The fixture is 1280x720, so examples meant for taller screenshots are not exercised here.
