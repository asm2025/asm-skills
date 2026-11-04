# essential-skills

Agent skills. Each folder under `skills/` is self-contained: a `SKILL.md` the agent follows, plus any `scripts/` and `references/` it uses.

| Skill | What it does |
|---|---|
| [`document-website`](skills/document-website/SKILL.md) | Screenshots a website with the Playwright MCP, annotates the screenshots (arrows, numbered badges, highlight boxes, labels), and builds a step-by-step tutorial as Word, Markdown, or self-contained HTML, and as PDF when you ask for one. A style file styles the markers and the document; see the [style file example](skills/document-website/references/style-file.md). |

## What `document-website` can do

- **Capture pages, including ones that scroll inside a box.** It screenshots through the Playwright MCP. When the page's content scrolls inside a panel instead of the window (app shells, a scrolling `body`), it detects that box and grows the window so the whole content lands in one screenshot. See [full page](skills/document-website/references/full-page.md).
- **Annotate screenshots.** Arrows, numbered circles, highlight boxes, and text labels, with right-to-left text support. The marker schema is in the [annotation spec](skills/document-website/references/annotation-spec.md).
- **Color markers from options or a style file.** Colors come from the marker itself, then `--color`/`--bg`/`--fg`, then a JSON style file (`--style`), then the built-in defaults.
- **Keep markers readable automatically.** Auto-contrast samples the pixels around each marker and swaps a color that would blend into the screenshot (and the text inside circles and labels), with a `[warn]` line for every change. Turn it off with `--no-auto-contrast`, per marker, or in the style file.
- **Build the tutorial as Word, Markdown, HTML, or PDF.** The `--output` extension picks the format. PDF is only made when you ask for it, through Word (Windows), LibreOffice, or Chrome/Edge, whichever is installed (`--pdf-engine` forces one).
- **Follow your template or a reference document.** Build inside a Word `.docx` or `.dotx` template (`--template`) and keep its styles, page setup, headers, and footers. Or have the agent copy the look and structure of a Word or PDF reference document; `describe_docx.py` prints a Word file's fonts, colors, page setup, and outline. See [templates and reference documents](skills/document-website/references/templates.md).
- **Style the document from the same style file.** Fonts, sizes, colors, alignment, and page size and margins for Word and PDF output, plus CSS for HTML (`--css`). The style file wins over a template for the keys it names. See the [style file example](skills/document-website/references/style-file.md).
- **Use any Playwright browser mode and keep a sign-in.** Headed, headless, isolated, or your own Chrome (through a second server). A saved sign-in goes only in a git-ignored temp folder and is a live session secret, never to be committed. See [browser modes](skills/document-website/references/browser-modes.md).

## Install

### Claude Code (plugin)

```
/plugin marketplace add asm2025/essential-skills
/plugin install essential-skills@essential-skills
```

This installs every skill under `skills/` and registers the [Playwright MCP server](https://github.com/microsoft/playwright-mcp) (`npx @playwright/mcp@latest`, so Node.js must be installed). Run `/plugin marketplace update essential-skills` to get new versions.

If Playwright MCP is already registered another way (for example, the official `playwright` plugin), you will end up with two copies of the server. Keep this plugin's `playwright` server enabled and disable the other in `/mcp`: only this one turns on the storage tools that save and restore a sign-in. The skill still works on another Playwright server, minus saved sign-in. For headless, isolated, and own-Chrome modes and saved sign-in, see [browser modes](skills/document-website/references/browser-modes.md).

### Other agents

```
npx skills add asm2025/essential-skills
```

Or copy a skill's folder into your agent's skills directory, for example `~/.claude/skills/document-website/` (all projects) or `.claude/skills/document-website/` (one project) for Claude Code. The scripts are found relative to the skill's own folder, so any location works. Register the Playwright MCP server with your agent yourself.

### Where the skills end up

| Install method | Skill folder |
|---|---|
| Claude Code plugin | `~/.claude/plugins/cache/essential-skills/essential-skills/<version>/skills/<skill>/` |
| Manual copy, all projects | `~/.claude/skills/<skill>/` |
| Manual copy, one project | `<project>/.claude/skills/<skill>/` |
| `npx skills add` | Printed by the command; it depends on the agent you pick |

`~` is your home folder (`C:\Users\<you>` on Windows). `<version>` is the `version` in `.claude-plugin/plugin.json`, for example `1.0.0`; each update adds a new folder. You rarely need the path yourself: when a skill runs, Claude Code tells the agent the skill's base directory, and the scripts are found from there.

## Requirements

`document-website` needs Python 3 with the packages in [`skills/document-website/requirements.txt`](skills/document-website/requirements.txt): `Pillow` and `python-docx`. `python-docx` is needed for Word output, for `.pdf` made by Word or LibreOffice, and for `describe_docx.py`; it is not needed for `.md`, `.html`, or a `.pdf` made by Chrome. `Pillow` is needed by every script, including every `build_docx.py` run (it reads the style file). For `.pdf` output you also need one PDF engine installed: Word (Windows only), LibreOffice, or Chrome/Edge. No Python package is involved, and no PDF is made unless you ask for one. For Arabic, Hebrew, and other right-to-left marker text, also install `arabic-reshaper python-bidi` (not needed when Pillow is built with libraqm).

You do not have to install them in advance: the skill checks them before it starts and asks before installing anything missing. Packages must go into the Python the agent runs as `python` (Windows) or `python3` (macOS and Linux).

### With pip

```bash
python -m pip install -r <skill-folder>/requirements.txt
```

Use `python3` on macOS and Linux. `<skill-folder>` is from the table above, or `skills/document-website` in a clone of this repo.

### With uv

Keep the packages in their own virtual environment, and activate it before starting the agent, so the agent's `python` is the one from that environment.

Create it once:

```bash
uv venv ~/.venvs/essential-skills
```

Activate it, install the packages (`uv pip install` targets the active environment), and start the agent from the same terminal:

```bash
# macOS and Linux
source ~/.venvs/essential-skills/bin/activate
# Windows PowerShell
~\.venvs\essential-skills\Scripts\Activate.ps1
# Windows Git Bash
source ~/.venvs/essential-skills/Scripts/activate

uv pip install -r <skill-folder>/requirements.txt
claude
```

Next time, only activate it and start the agent. If you would rather install into your existing Python without a virtual environment, use `uv pip install --system -r <skill-folder>/requirements.txt`; on Linux distributions and Homebrew Python, which mark the system Python as externally managed, use the virtual environment instead.
