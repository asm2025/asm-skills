# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of agent skills (remote: `asm2025/asm-skills`). Each skill is a self-contained folder under `skills/<name>/`:

- `SKILL.md`: YAML frontmatter (`name`, `description`) plus the workflow the agent follows. The `description` is the trigger; word it for when the skill should fire.
- `scripts/`: standalone Python CLIs the workflow shells out to.
- `references/`: detail disclosed from `SKILL.md`, loaded only when the workflow points at it.

There is no build system, package manifest, linter, or test suite. Verification means running the scripts.

## Running the scripts

Dependencies: `pip install Pillow python-docx` (optional, for right-to-left marker text: `arabic-reshaper python-bidi`). On Windows the interpreter is usually `python`, not `python3`.

```bash
python skills/document-website/scripts/annotate.py --help
python skills/document-website/scripts/build_docx.py --help
```

Smoke-test a change with the verification skill (see "Verifying changes" below), which runs the scripts end to end and keeps inputs and outputs outside the repo.

## document-website skill

Pipeline: Playwright MCP screenshots, then `annotate.py` draws markers on them, then `build_docx.py` assembles the tutorial as `.docx`, `.md`, or `.html` (chosen by the `--output` extension).

- `annotate.py` dispatches marker types through the `DRAWERS` dict. `references/annotation-spec.md` is the user-facing schema for the same markers; any marker type, field, default, warning, or exit-code change goes in both places.
- `build_docx.py` reads a `steps.json` array of `{heading?, body?, image?, caption?}` (`image` may be a list). That format is also documented in `SKILL.md` step 5; keep the two in sync.
- `screenshot_dir.py` picks the screenshots folder (`--dir`, then `DOCUMENT_WEBSITE_SCREENSHOTS`, then `<temp>/screenshots` for a project temp folder, then `screenshots/`). Its rules are also documented in `SKILL.md` step 1; keep the two in sync.
- Script paths in `SKILL.md` use `<skill-dir>` (the folder holding `SKILL.md`), so they work wherever the skill is installed. Never write repo-root paths like `skills/document-website/scripts/...` there.

## Verifying changes

`.claude/skills/verify-document-website/` drives both scripts the way the workflow does and checks pixels and document structure. Use it after any change under `skills/document-website/`, and update its `features/` recipes in the same change when behavior changes.
