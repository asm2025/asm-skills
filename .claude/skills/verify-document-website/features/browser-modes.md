# Browser modes and saved sign-in

The plugin registers a `playwright` MCP server with the storage tools turned on, so the agent can save a sign-in and restore it later, including in headless mode. `references/browser-modes.md` documents the modes (headless, isolated, saved sign-in, the user's own Chrome) and where a saved sign-in file may go.

## Sub-features

- `modes-caps` lists the MCP tools with and without the storage capability.
- `modes-headless` starts the server headless and takes a screenshot with no window.
- `modes-caps-replaced` shows `--caps=storage` replacing a `PLAYWRIGHT_MCP_CAPS` value, and `--caps=storage,vision` keeping both.
- `modes-plugin-json` checks the plugin's storage setting and version.
- `modes-auth-path` proves the documented sign-in path is git-ignored and the old `<shots>/../auth` path was not.

## How to get to it (user POV)

- The agent follows `references/browser-modes.md` and `SKILL.md` step 2 (Sign-in). The user sets `PLAYWRIGHT_MCP_*` variables in the shell before starting the agent, or reads the plugin's `plugin.json`.

## Driving it with vdw

Preconditions:

- Baseline state from `README.md`. Node.js and `npx` are on `PATH`; the first `npx` call downloads `@playwright/mcp` (about 20 s).
- Write the throwaway MCP client to `$RUN/work/mcp_probe.py` (it speaks MCP over stdio: `initialize`, `notifications/initialized`, `tools/list`, and with `--shot` also `browser_navigate` to `about:blank` and `browser_take_screenshot`; it prints one tool name per line, then kills the whole process tree):

```bash
cat > "$RUN/work/mcp_probe.py" <<'PYEOF'
import json, os, shutil, subprocess, sys, threading, queue

def main():
    argv = sys.argv[1:]
    shot = "--shot" in argv
    argv = [a for a in argv if a != "--shot"]
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    cmd = [npx, "-y", "@playwright/mcp@latest"] + argv
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, cwd=os.environ.get("MCP_CWD"))
    q = queue.Queue()
    threading.Thread(target=lambda: [q.put(l) for l in p.stdout], daemon=True).start()
    def send(m):
        p.stdin.write((json.dumps(m) + "\n").encode()); p.stdin.flush()
    def rpc(i, method, params=None):
        send({"jsonrpc": "2.0", "id": i, "method": method, "params": params or {}})
        while True:
            m = json.loads(q.get(timeout=120))
            if m.get("id") == i:
                return m
    try:
        rpc(1, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                              "clientInfo": {"name": "vdw", "version": "0"}})
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        r = rpc(2, "tools/list")
        for t in sorted(t["name"] for t in r["result"]["tools"]):
            print(t)
        if shot:
            r = rpc(3, "tools/call", {"name": "browser_navigate", "arguments": {"url": "about:blank"}})
            print("navigate isError:", r["result"].get("isError", False))
            r = rpc(4, "tools/call", {"name": "browser_take_screenshot", "arguments": {"type": "png"}})
            print("screenshot isError:", r["result"].get("isError", False),
                  "image:", any(c.get("type") == "image" for c in r["result"]["content"]))
            if os.environ.get("MCP_KEEP"):
                out = subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'ms-playwright' -and $_.Name -match 'chrome|msedge|headless' } | Select-Object -First 1 -ExpandProperty CommandLine"],
                    capture_output=True, text=True).stdout.strip()
                print("BROWSER:", out.split(" --")[0])
                print("HEADLESS_FLAG:", "--headless" in out.split())
    finally:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        else:
            p.kill()

main()
PYEOF
```

- **Caps on.** Run `"$PY" "$VDW" run --run "$RUN" --name modes-caps-on -- env PLAYWRIGHT_MCP_CAPS=storage "$PY" "$RUN/work/mcp_probe.py"`. Exit `0`; stdout lists `browser_storage_state` and `browser_set_storage_state`.
- **Caps on by flag.** Run the same with `"$PY" "$RUN/work/mcp_probe.py" --caps=storage` and no variable, under `--name modes-caps-flag`. The same two tools are listed. This is the form `plugin.json` uses.
- **Caps off.** Run `"$PY" "$VDW" run --run "$RUN" --name modes-caps-off -- "$PY" "$RUN/work/mcp_probe.py"` with `PLAYWRIGHT_MCP_CAPS` unset in the calling shell. Neither storage tool is listed.
- **Headless.** Run `"$PY" "$VDW" run --run "$RUN" --name modes-headless -- env PLAYWRIGHT_MCP_HEADLESS=true MCP_KEEP=1 "$PY" "$RUN/work/mcp_probe.py" --shot`. Stdout has `navigate isError: False` and `screenshot isError: False image: True`, and `HEADLESS_FLAG: True` shows that the Chromium command line (found by its `ms-playwright` profile folder) contains `--headless`. No browser window appears.
- **Plugin file.** Run `"$PY" "$VDW" run --run "$RUN" --name modes-plugin-json -- "$PY" -c "import json; d=json.load(open('.claude-plugin/plugin.json',encoding='utf-8')); a=d['mcpServers']['playwright']['args']; assert '--caps=storage' in a, a; assert d['version']=='1.1.0', d['version']; print('ok', a, d['version'])"`. Exit `0`. Then, if `claude plugin validate --help` works, `"$PY" "$VDW" run --run "$RUN" --name modes-plugin-validate -- claude plugin validate .` passes; otherwise report it skipped, naming that the CLI lacks the command.
- **Sign-in path.** Build a throwaway repo: `mkdir -p "$RUN/work/authrepo/tmp/auth" && ( cd "$RUN/work/authrepo" && git init -q && printf 'tmp/\n\!tmp/\n' > .gitignore && mkdir -p '!tmp/auth' )`. Then record each check with `vdw run`, using `-- git -C "$RUN/work/authrepo" check-ignore -q tmp/auth/example.com.json`: exit `0` (name `modes-auth-ignored`). `... check-ignore -q auth/example.com.json` (where `<shots>/../auth` lands with no temp folder): exit `1` (name `modes-auth-not-ignored`). Quote a `!tmp` path (history expansion eats it unquoted): `... check-ignore -q '!tmp/auth/example.com.json'` exits `0` (name `modes-auth-bang-ignored`), the form `references/browser-modes.md` shows.
- **Caps replaced.** Run `"$PY" "$VDW" run --run "$RUN" --name modes-caps-replaced -- env PLAYWRIGHT_MCP_CAPS=vision "$PY" "$RUN/work/mcp_probe.py" --caps=storage`. Both storage tools are listed and the vision tools (`browser_mouse_click_xy` and its siblings) are not: the flag replaces the variable. Then `"$PY" "$RUN/work/mcp_probe.py" --caps=storage,vision` under `--name modes-caps-both` lists the storage tools and the vision tools together, which is the registration `references/browser-modes.md` shows for extra capabilities.
- **Proof.** `$RUN/evidence/modes-*.txt` hold the records.

## Gotchas

- Do not wrap commands in `bash -c` under `vdw run`: on Windows that can resolve to WSL's bash, which cannot see `C:/` paths. Use `git -C <dir>` instead.
- Stray processes: `mcp_probe.py` kills the process tree at the end, but check afterwards (`tasklist | grep -i -E "node|chrome|headless"` or the PowerShell equivalent) that nothing it started remains. Do not kill Chrome windows that were already open.
- `PLAYWRIGHT_MCP_CAPS` is read by the server at start; changing it needs a new process, which is why each bullet starts its own.
- The `--caps=storage` argument wins over `PLAYWRIGHT_MCP_CAPS`, so "Caps off" must run without the flag.
- Never save a real sign-in file in this recipe. The throwaway repo only proves the `git check-ignore` rule; no storage-state file is written.
