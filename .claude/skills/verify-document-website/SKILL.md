---
name: verify-document-website
description: Prove that the document-website skill's scripts work by running them the way the skill's workflow does. Runs annotate.py on a real PNG and build_docx.py on a real steps.json, then checks the output pixels and the .docx structure, saving evidence outside the repo. Use after changing anything under skills/document-website/ (annotate.py, build_docx.py, SKILL.md, annotation-spec.md), when a marker type or steps.json field is added or changed, or when asked to verify, smoke-test, or prove the document-website pipeline.
---

# Verify document-website

The thing under test is `skills/document-website/`: two Python CLIs that an agent runs while it follows that skill's `SKILL.md`.

- `scripts/annotate.py` draws markers (`arrow`, `circle`, `box`, `label`) onto a PNG.
- `scripts/build_docx.py` turns a `steps.json` array into a tutorial: `.docx`, `.md`, or `.html`, by the `--output` extension.
- `scripts/screenshot_dir.py` picks and creates the folder the screenshots go in.

The "user" is an agent that copies commands and JSON from `skills/document-website/SKILL.md` and `references/annotation-spec.md`. Verify by running those commands, not by importing functions. The Playwright screenshot and coordinate steps are agent actions, not scripts. Only `features/tutorial-pipeline.md` touches them.

Harness: `.claude/skills/verify-document-website/scripts/vdw.py` (called `vdw` below). Run every command from the repo root in Git Bash or another POSIX shell.

## Launch

There is no server. "Launch" means: an isolated venv with the dependencies, plus a fresh run directory outside the repo.

```bash
VDW=.claude/skills/verify-document-website/scripts/vdw.py
eval "$(python "$VDW" setup | sed 's/^/export /')"   # sets PY, RUN, and SHOTS
echo "PY=$PY RUN=$RUN SHOTS=$SHOTS"
```

- Use `python` on Windows, `python3` on macOS/Linux, for this one call only. From here on, use `"$PY"` (the venv interpreter) for everything.
- `setup` creates `<tempdir>/verify-document-website/venv` the first time (about 20 s with network) and reuses it after that. It runs `pip install Pillow python-docx pypdf arabic-reshaper python-bidi` each time, which is a no-op when they are already installed.
- Every `setup` call makes a new `RUN=<tempdir>/verify-document-website/runs/<timestamp>-<pid>/` with `work/` (inputs, scratch) and `evidence/` (proof).
- `SHOTS=<screenshots folder>/vdw-<run id>` is where browser screenshots go: the Playwright MCP refuses to write outside the repo. The screenshots folder is the one the skill's `screenshot_dir.py` picks for the repo (`<repo>/screenshots/`, git-ignored, unless the repo has a temp folder). `cleanup` deletes `$SHOTS`, and the screenshots folder too when it is left empty; copy anything you keep into `$RUN`.
- Ready means `doctor` exits 0.

Parallel runs: each `setup` call gets its own `RUN`, so runs never share files. The venv is shared, so run `setup` once on its own before starting parallel runs, so that two first-time `pip install`s do not race.

Never install the dependencies into the user's global Python, and never write inputs or outputs inside the repo.

## Doctor

```bash
"$PY" "$VDW" doctor --run "$RUN"
```

It is read-only. It checks that the run dir exists and is outside the repo, that both scripts exist, and that Pillow and python-docx import. It also prints the repo HEAD (and flags uncommitted changes under `skills/`), the Python version and `utf8_mode`, which font `annotate.py` picks for Latin, symbol, and CJK text, and whether right-to-left text can be shaped. Run it first, and again whenever an output looks wrong. A `FAIL` line means stop and fix the environment before driving anything.

Write the doctor output into the evidence: `"$PY" "$VDW" doctor --run "$RUN" > "$RUN/evidence/doctor.txt"`.

## Drive

Every drive is a real CLI call wrapped in `vdw run`, which runs it from the repo root and saves the command, exit code, stdout, and stderr to `$RUN/evidence/<name>.txt`:

```bash
"$PY" "$VDW" run --run "$RUN" --name <name> -- "$PY" skills/document-website/scripts/annotate.py ...
"$PY" "$VDW" run --run "$RUN" --name <name> -- "$PY" skills/document-website/scripts/build_docx.py ...
```

On Windows, `run --lock <file>` holds that file open with no sharing while the command runs, the way Word holds an open document.

Inputs:

- `"$PY" "$VDW" fixture --out "$RUN/work/page.png"` writes a 1280x720 synthetic web page with known colors: background `(245,246,248)`, a dark header, two blue `(25,118,210)` buttons, and a white form field. None of them is the default marker red `(229,57,53)`, so any red pixel came from a marker.
- Prefer a real screenshot when the session has a browser tool that saves PNGs (see `features/tutorial-pipeline.md`). The fixture is a stand-in for that.

Observing output:

- `"$PY" "$VDW" probe --image <png> --at x,y [--at x,y ...]` prints exact RGB at points. Use probes as assertions.
- `"$PY" "$VDW" find --image <png> --color r,g,b [--tolerance n] [--region x0,y0,x1,y1]` prints the count, bounding box, and center of pixels matching a color. Use it to check where text or a marker landed.
- `"$PY" "$VDW" diff --before <in> --after <out> [--region x0,y0,x1,y1]` prints the count and bounding box of changed pixels, and fails on a size mismatch.
- `"$PY" "$VDW" docx-dump --docx <file> --out "$RUN/evidence/<name>.dump.txt"` lists every paragraph with its style, alignment, image width, first-run formatting, and text.
- Look at each output PNG yourself (read the image). Probes prove that the pixels are there, and looking catches wrong placement or clipped text.

Recipes per feature: [`features/README.md`](features/README.md).

## Evidence

Everything lives in `$RUN/evidence/`:

- `doctor.txt`
- `<name>.txt` from each `vdw run`: the command, cwd, exit code, stdout, stderr
- output PNGs and `.docx` files (write outputs straight into `evidence/`, and inputs into `work/`)
- `*.dump.txt` from `docx-dump`, plus probe and diff output, which you paste or redirect into `evidence/`

Proof standards:

- Run the real CLIs with the documented flags. Never import `annotate()` or `build()` to "test" them.
- A command's exit code 0 is not proof. Show the effect: probed pixels for markers, `docx-dump` lines for the document.
- `build_docx.py` exits 1 when an image is missing, but still saves the document with a red `[Image not found: ...]` paragraph. Check both the exit code and the dump.
- Encoding bugs hide on Python 3.15+, which reads files as UTF-8 by default. Prove UTF-8 handling with `"$PY" -X utf8=0 ...`, as the feature recipes do.
- Check the negative too: a box's interior stays background, an unknown marker type changes no pixels.
- When you change a script, prove the changed path and at least one unchanged path from the feature map.
- Report the `RUN` path, the HEAD from doctor, and which feature IDs you proved.

## Cleanup

```bash
"$PY" "$VDW" cleanup --run "$RUN"          # deletes $RUN/work, keeps $RUN/evidence
"$PY" "$VDW" cleanup --run "$RUN" --venv   # also deletes the shared venv (rarely needed)
```

`cleanup` refuses any path outside `<tempdir>/verify-document-website/`. There are no processes to kill. Evidence stays at `$RUN/evidence/` until the user deletes it. After cleanup, `ls "$RUN/evidence"` must still list the proof files.

## Helpers

`vdw.py` is the only helper. `"$PY" "$VDW" --help` and `"$PY" "$VDW" <subcommand> --help` show every flag. Its subcommands are `setup`, `doctor`, `fixture`, `page`, `run`, `probe`, `find`, `diff`, `docx-dump`, `template`, and `cleanup`. Use `--root DIR` (before the subcommand) to put the venv and runs somewhere other than the system temp dir.

Keep this skill in sync with the scripts. When `DRAWERS` in `annotate.py`, `references/annotation-spec.md`, or the `steps.json` format changes, update the matching feature file in the same change.
