# document-website verification map

This directory is the maintained source for verifying the user-facing behavior of `skills/document-website/`. The "user" is an agent following that skill's `SKILL.md`. Read this index before driving the scripts, then use the matching feature file as the recipe.

## Baseline preconditions

- Run all commands from the repo root in a POSIX shell (Git Bash on Windows).
- `VDW=.claude/skills/verify-document-website/scripts/vdw.py`.
- `PY` and `RUN` come from a fresh `setup` call in this verification run (see `../SKILL.md` Launch). Never reuse another run's `RUN`.
- `"$PY" "$VDW" doctor --run "$RUN"` exits 0, and its output is saved to `$RUN/evidence/doctor.txt`.
- `"$PY" "$VDW" fixture --out "$RUN/work/page.png"` has written the baseline input image.

## Driving conventions

- Start every recipe from the baseline state unless its preconditions say otherwise.
- Wrap every script call in `"$PY" "$VDW" run --run "$RUN" --name <id> -- ...`, so the command, exit code, and output are recorded.
- Write inputs to `$RUN/work/` and outputs to `$RUN/evidence/`.
- Treat every command as literal. Keep the JSON, coordinates, and flags unchanged. The expected pixel values below depend on them.
- Use `"$PY"`, never `python3`, for the scripts under test. The venv is what has the dependencies.

## Proof and skip reporting

- Marker proof is `probe` output at the listed points plus a look at the output PNG.
- Document proof is a `docx-dump` saved to `$RUN/evidence/`.
- CLI proof is the `vdw run` record: command, stdout, stderr, exit code.
- Record the feature ID with each artifact (use it as the `--name`).
- Report an unreachable path with the attempted command and the unmet precondition.
- Do not report a skipped entry point as verified through a different path. A fixture image does not prove the Playwright screenshot step.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with vdw` starts with `Preconditions:` and uses labeled bullets that pair each user action with an exact command and observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

Keep implementation details out of the map. Name only user paths, stable handles, required state, commands, and observable proof.

## Features

- [Annotate markers](./annotate-markers.md) covers all four marker types with default and custom fields, colors, arrow tail flipping, text centering, UTF-8 marker files, font fallback, and right-to-left text.
- [Annotation input checks](./annotate-checks.md) covers invalid markers and JSON, missing files, unknown types, off-image markers, missing glyphs, `--font`, and unshaped right-to-left text.
- [Annotate style file and color defaults](./annotate-style.md) covers `--color`, `--bg`, `--fg`, and `--style`: command-line colors, style file defaults and per-type blocks, precedence, and style file errors and warnings.
- [Annotate auto-contrast](./annotate-contrast.md) covers swapping marker colors that blend into the screenshot: the four-strip contrast fixture, palette order, text color, the off switches, `min_contrast`, off-image markers, warning counts, and speed on a very tall image.
- [Build the Word tutorial](./build-docx.md) covers title, headings, paragraphs, image lists and sizing, captions, default headings, relative image lookup, missing and unreadable images, invalid steps, UTF-8 with a byte order mark, output folders, and locked output files.
- [Build inside a Word template](./build-template.md) covers `--template` with `.docx` and `.dotx` files: carried-over styles, headers, footers, and page setup, missing styles, ignored for `.md` and `.html`, bad template errors, and unchanged output without a template.
- [Build Markdown and HTML tutorials](./build-md-html.md) covers structure, copied Markdown images, escaping, embedded HTML images, rebuilds, and missing images for `.md` and `.html` output.
- [Screenshots folder](./screenshot-dir.md) covers how the screenshots folder is picked: `--dir`, the environment variable, project temp folders, the default, `--sub`, `--project`, and the outside-the-project warning.
- [Documented examples](./spec-examples.md) covers running every JSON and command example from `annotation-spec.md` and `SKILL.md` as written, from a project outside the repo.
- [Tutorial pipeline](./tutorial-pipeline.md) covers screenshot, element coordinates, annotation, and `.docx`, end to end.
