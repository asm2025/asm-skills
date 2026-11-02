# Screenshots folder

`screenshot_dir.py` picks the folder a tutorial's screenshots, marker files, and `steps.json` go in, creates it, and prints its absolute path. A folder the user names wins; otherwise a project temp folder is used; otherwise `screenshots/` in the project folder.

## Sub-features

- `shots-default` uses `<project>/screenshots` when nothing else applies.
- `shots-temp` uses `<temp>/screenshots` for the first existing temp folder, in the order `!tmp`, `tmp`, `temp`, `.tmp`, `.temp`.
- `shots-dir` uses `--dir`, relative to the project folder or absolute.
- `shots-env` uses `DOCUMENT_WEBSITE_SCREENSHOTS` when `--dir` is not given; `--dir` wins over it.
- `shots-sub` adds `--sub <name>` under whichever folder was picked.
- `shots-project` takes the project folder from `--project`, and rejects a missing one with exit 2.
- `shots-outside` warns when the folder is outside the project, where the Playwright MCP cannot save.

## How to get to it (user POV)

- Run `python3 <skill-dir>/scripts/screenshot_dir.py` from the project folder, as in `SKILL.md` step 1, optionally with `--dir`, `--sub`, or `--project`.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`.
- `D=$("$PY" -c 'import pathlib; print(pathlib.Path("skills/document-website/scripts/screenshot_dir.py").resolve().as_posix())')`, an absolute path to the script that Windows Python can open from any folder.
- `mkdir -p "$RUN/work/proj"`. Each bullet runs in a subshell `( cd "$RUN/work/proj" && ... )` so the current folder is the project. Save each bullet's stdout and stderr to `$RUN/evidence/shots-<id>.txt` (`> file 2>&1; echo "exit $?" >> file`).

- **Default.** Run `( cd "$RUN/work/proj" && "$PY" -B "$D" )`. Stderr `[info] screenshots folder (default): .../proj/screenshots`, stdout the same path, and the folder exists.
- **Temp folder.** Run `mkdir -p "$RUN/work/proj/tmp" "$RUN/work/proj/!tmp"`, then the same command. Stderr names `project temp folder !tmp/`, and stdout ends in `/proj/!tmp/screenshots` (`!tmp` comes before `tmp`).
- **Sub.** Run `( cd "$RUN/work/proj" && "$PY" -B "$D" --sub login )`. Stdout ends in `/proj/!tmp/screenshots/login`, and the folder exists.
- **Dir.** Run `( cd "$RUN/work/proj" && "$PY" -B "$D" --dir docs/img )`. Stderr `(set by --dir)`, stdout ends in `/proj/docs/img`.
- **Environment.** Run `( cd "$RUN/work/proj" && DOCUMENT_WEBSITE_SCREENSHOTS=envshots "$PY" -B "$D" )`: stderr `(set by DOCUMENT_WEBSITE_SCREENSHOTS)`, stdout ends in `/proj/envshots`. Then `( cd "$RUN/work/proj" && DOCUMENT_WEBSITE_SCREENSHOTS=envshots "$PY" -B "$D" --dir cli )`: stdout ends in `/proj/cli`.
- **Outside the project.** Run `( cd "$RUN/work/proj" && "$PY" -B "$D" --dir "$RUN/work/elsewhere" )`. Exit `0`, stdout ends in `/work/elsewhere`, and stderr has `[warn] this folder is outside the project; the Playwright MCP only saves screenshots inside its allowed roots`.
- **Project argument.** From the repo root, run `"$PY" -B "$D" --project "$RUN/work/proj"`: stdout ends in `/proj/!tmp/screenshots`. Then `"$PY" -B "$D" --project "$RUN/work/nope"`: exit `2`, stderr `[error] project folder not found`.
- **Proof.** `$RUN/evidence/` holds the `shots-*.txt` records.

## Gotchas

- In an interactive bash shell, `!tmp` unquoted triggers history expansion. Quote it, as above.
- `-B` stops Python from writing `__pycache__` next to the script in the repo.
- Use the `D` from the preconditions: in Git Bash, a path built from `$(pwd)` reads as `/d/...`, which Windows Python opens as `C:\d\...`.
