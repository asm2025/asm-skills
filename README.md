# essential-skills

Agent skills. Each folder under `skills/` is self-contained: a `SKILL.md` the agent follows, plus any `scripts/` and `references/` it uses.

| Skill | What it does |
|---|---|
| [`document-website`](skills/document-website/SKILL.md) | Screenshots a website with the Playwright MCP, annotates the screenshots (arrows, numbered badges, highlight boxes, labels), and builds a step-by-step tutorial as Word, Markdown, or self-contained HTML. |

## Install

### Claude Code (plugin)

```
/plugin marketplace add asm2025/essential-skills
/plugin install essential-skills@essential-skills
```

This installs every skill under `skills/` and registers the [Playwright MCP server](https://github.com/microsoft/playwright-mcp) (`npx @playwright/mcp@latest`, so Node.js must be installed). Run `/plugin marketplace update essential-skills` to get new versions.

If Playwright MCP is already registered another way (for example, the official `playwright` plugin), you will end up with two copies of the server. Disable one of them in `/mcp`.

### Other agents

```
npx skills add asm2025/essential-skills
```

Or copy a skill's folder into your agent's skills directory, for example `~/.claude/skills/document-website/` (all projects) or `.claude/skills/document-website/` (one project) for Claude Code. The scripts are found relative to the skill's own folder, so any location works. Register the Playwright MCP server with your agent yourself.

## Requirements

`document-website` needs Python 3 with the packages in [`skills/document-website/requirements.txt`](skills/document-website/requirements.txt):

```bash
python -m pip install -r skills/document-website/requirements.txt
```

Use `python3` on macOS and Linux. Install with the same interpreter that will run the scripts. `python-docx` is needed only for Word output. For Arabic, Hebrew, and other right-to-left marker text, also install `arabic-reshaper python-bidi` (not needed when Pillow is built with libraqm).

You do not have to install them in advance: the skill checks them before it starts and asks before installing anything missing.
