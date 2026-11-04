# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of agent skills (remote: `asm2025/essential-skills`). Each skill is a self-contained folder under `skills/<name>/`:

- `SKILL.md`: YAML frontmatter (`name`, `description`) plus the workflow the agent follows. The `description` is the trigger; word it for when the skill should fire.
- `scripts/`: standalone Python CLIs the workflow shells out to.
- `references/`: detail disclosed from `SKILL.md`, loaded only when the workflow points at it.
- `requirements.txt`: the Python packages its scripts import.

The repo is also a Claude Code plugin and its own marketplace (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`). The plugin ships every folder under `skills/` and registers the Playwright MCP server through `mcpServers` in `plugin.json`. That server lives in `plugin.json`, not in a root `.mcp.json`, so it does not also become a project MCP server when working in this repo. `.claude/skills/` holds dev-only skills and is not shipped. Bump `version` in `plugin.json` when a release should reach installed copies.

There is no build system, package manifest, linter, or test suite. Verification means running the scripts.

## Running the scripts

Dependencies: `python -m pip install -r skills/document-website/requirements.txt` (optional, for right-to-left marker text: `arabic-reshaper python-bidi`). On Windows the interpreter is usually `python`, not `python3`. When a script gains or drops an import, update `requirements.txt`, the Dependencies table in `SKILL.md`, and the README's Requirements section together.

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

## Plans and specs

Design specs go in `docs/specs/`, implementation plans in `docs/plans/`, both git-tracked and committed with the work. Files are numbered: `<n>. <Title>.md` (for example `docs/specs/1. Document Website Capture and Styling.md`). A spec and the plan built from it share the same number. Take the next number after the highest one in either folder. Companion files keep the plan's name with a suffix: `<n>. <Title>-deferred.md` and `<n>. <Title>-verification.md`.

## Scratch directory

`!tmp/` at the repo root is a temporary directory for throwaway things that need testing and do not need tracking. It is git-ignored (`\!tmp/` in `.gitignore`; the backslash stops the leading `!` from negating the pattern). Put scratch inputs and outputs there, not in tracked folders.

## Verifying changes

`.claude/skills/verify-document-website/` drives both scripts the way the workflow does and checks pixels and document structure. Use it after any change under `skills/document-website/`, and update its `features/` recipes in the same change when behavior changes.
