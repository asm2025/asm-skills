# Browser modes and saved sign-in

The Playwright MCP server decides how the browser runs. The mode is fixed when the server starts, so changing it means restarting the server (`/mcp`, then reconnect) or starting a new session. The agent cannot switch modes mid-session.

## Default

Headed browser with Playwright's persistent profile for the project. The user signs in once in the Playwright window and stays signed in on later runs in the same project. This is the default because it needs no setup and survives restarts.

## Modes

Set these as environment variables in the shell before starting the agent, then restart the server.

| Mode | Setting | Notes |
|---|---|---|
| Headless | `PLAYWRIGHT_MCP_HEADLESS=true` | No window, so no interactive sign-in. Pair it with a saved sign-in or a profile that is already signed in. |
| Isolated | `PLAYWRIGHT_MCP_ISOLATED=true` | A clean browser each session; nothing is kept. |
| Saved sign-in at start | `PLAYWRIGHT_MCP_STORAGE_STATE=<file>` (with isolated) | Loads cookies and local storage from a file saved earlier. |
| Own Chrome or Edge | `PLAYWRIGHT_MCP_EXTENSION=true` | Needs the Playwright extension in that browser; drives real tabs with the real sign-in. `PLAYWRIGHT_MCP_PROFILE_DIR_NAME` picks the profile. |
| Chosen profile folder | `PLAYWRIGHT_MCP_USER_DATA_DIR=<dir>` | A persistent profile in a known place. |
| Browser | `PLAYWRIGHT_MCP_BROWSER=chrome\|msedge\|firefox\|webkit` | |
| Output folder | `PLAYWRIGHT_MCP_OUTPUT_DIR=<dir>` | Where page snapshots and logs go instead of `<project>/.playwright-mcp/`. |
| Several at once | `PLAYWRIGHT_MCP_CONFIG=<file.json>` | Playwright MCP's own config file. |

## Saved sign-in

This plugin starts its server with `--caps=storage`, which adds `browser_storage_state` and `browser_set_storage_state`. The flag replaces any `PLAYWRIGHT_MCP_CAPS` value, so capabilities set there are lost. To turn the storage tools off, register the server yourself without the flag. To keep other capabilities too, register your own server with them listed together, for example `--caps=storage,vision`, and disable this plugin's `playwright` server in `/mcp` so only one Playwright server runs (see "Keep one Playwright server enabled"):

```
claude mcp add playwright-vision -- npx @playwright/mcp@latest --caps=storage,vision
```

A saved sign-in file is a live session secret: anyone who has it can act as the user on that site. It must never be committed or put in a tracked folder.

1. **Pick the path.** `<temp>/auth/<host>.json`, where `<temp>` is the first project temp folder that exists: `!tmp`, `tmp`, `temp`, `.tmp`, `.temp` (the folders `screenshot_dir.py` looks for). Do not derive it from the screenshots folder: with no temp folder that folder is `<project>/screenshots`, and with `--dir` it can be any tracked folder. If the project has no temp folder, ask the user where to save the file.
2. **Check it is ignored.** In a git repo, run `git check-ignore -q '<path>'` (quote the path: an unquoted `!tmp` triggers history expansion in bash) and save only when it exits `0`. If it exits `1`, refuse and tell the user why: the path is not git-ignored, so the file could be committed. Offer to add the temp folder to `.gitignore` instead. Outside a git repo the command exits `128` and no check is possible: save only under the temp folder from step 1, and warn the user that the file is a live secret.
3. **Save** with `browser_storage_state`, after the user has signed in in the Playwright window. Create the `auth` folder first. Remind the user the file is a live session secret.
4. **Restore** later with `browser_set_storage_state`, in any mode including headless. Sessions expire, so if the site shows its sign-in page again, ask the user to sign in and save again.

## The user's own Chrome

To drive the user's own Chrome or Edge with its real sign-in, register a second server next to this one and install the Playwright extension in that browser:

```
claude mcp add playwright-chrome -- npx @playwright/mcp@latest --extension
```

When the user asks to "use my Chrome," use that server's tools. If it is not registered, give this one-line setup instead of guessing.

## Keep one Playwright server enabled

The official `playwright` plugin and this plugin each register a Playwright server. Two servers mean two browsers, and settings applied to one do not reach the other. Keep this plugin's `playwright` server enabled and disable the other in `/mcp`: only this one turns on the storage tools. The skill still works on any Playwright server, minus saved sign-in.
