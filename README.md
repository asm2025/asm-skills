# asm-skills

Agent skills. Each folder under `skills/` is self-contained: a `SKILL.md` the agent follows, plus any `scripts/` and `references/` it uses.

| Skill | What it does |
|---|---|
| [`document-website`](skills/document-website/SKILL.md) | Screenshots a website with the Playwright MCP, annotates the screenshots (arrows, numbered badges, highlight boxes, labels), and builds a step-by-step tutorial as Word, Markdown, or self-contained HTML. |

## Install a skill

Copy the skill's folder into your agent's skills directory, for example `~/.claude/skills/document-website/` (all projects) or `.claude/skills/document-website/` (one project) for Claude Code. The scripts are found relative to the skill's own folder, so any location works.

`document-website` also needs:

- Python 3 with `pip install Pillow python-docx` (and optionally `arabic-reshaper python-bidi` for right-to-left marker text)
- The [Playwright MCP server](https://github.com/microsoft/playwright-mcp) registered with your agent
