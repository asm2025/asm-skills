#!/usr/bin/env python3
"""
screenshot_dir.py - Pick (and create) the folder that screenshots go in.

Prints the folder's absolute path on stdout and how it was chosen on stderr.

Order of precedence:
  1. --dir PATH, or the DOCUMENT_WEBSITE_SCREENSHOTS environment variable
     (a relative path is taken from the project folder)
  2. <temp>/screenshots, where <temp> is the first of these folders that exists
     in the project folder: !tmp, tmp, temp, .tmp, .temp
  3. screenshots/ in the project folder

The project folder is --project, or the current folder.

Usage:
    python3 screenshot_dir.py
    python3 screenshot_dir.py --dir docs/images
    python3 screenshot_dir.py --project /path/to/project --sub login-flow
"""

import argparse
import os
import sys
from pathlib import Path

TEMP_FOLDERS = ["!tmp", "tmp", "temp", ".tmp", ".temp"]
ENV_VAR = "DOCUMENT_WEBSITE_SCREENSHOTS"


def resolve(project: Path, override: str = None):
    """Return (folder, reason)."""
    source = "--dir"
    if not override and os.environ.get(ENV_VAR):
        override, source = os.environ[ENV_VAR], ENV_VAR
    if override:
        p = Path(override).expanduser()
        return (p if p.is_absolute() else project / p), f"set by {source}"
    for name in TEMP_FOLDERS:
        if (project / name).is_dir():
            return project / name / "screenshots", f"project temp folder {name}/"
    return project / "screenshots", "default"


def main():
    parser = argparse.ArgumentParser(
        description="Pick and create the screenshots folder for document-website.")
    parser.add_argument("--project", default=".", help="Project folder (default: current folder)")
    parser.add_argument("--dir", help=f"Use this folder instead (also: ${ENV_VAR}); "
                                      "relative paths are taken from the project folder")
    parser.add_argument("--sub", help="Subfolder to add, for example one per tutorial")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"[error] project folder not found: {args.project}", file=sys.stderr)
        sys.exit(2)
    folder, reason = resolve(project, args.dir)
    if args.sub:
        folder = folder / args.sub
    folder = folder.resolve()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"[error] cannot create {folder}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[info] screenshots folder ({reason}): {folder.as_posix()}", file=sys.stderr)
    if project not in folder.parents and folder != project:
        print("[warn] this folder is outside the project; the Playwright MCP only saves "
              "screenshots inside its allowed roots (the project folder by default)", file=sys.stderr)
    print(folder.as_posix())


if __name__ == "__main__":
    main()
