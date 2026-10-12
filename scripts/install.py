#!/usr/bin/env python3
"""Select the native OS edition before installing the ArtCraft plugin."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def edition(platform: str, root: Path = ROOT) -> tuple[Path, str]:
    if platform == "win32":
        return root / "windows", "artcraft-windows"
    if platform == "darwin":
        return root, "artcraft-local"
    raise ValueError("Only native Windows and macOS are supported. Use Windows Python, not WSL, to control Windows apps.")


def plan(platform: str, python: str, codex: str, root: Path = ROOT) -> list[list[str]]:
    plugin_root, marketplace = edition(platform, root)
    plugin_name = "artcraft" if platform == "darwin" else "artcraft-agent"
    return [
        [python, str(plugin_root / "scripts/setup.py")],
        [codex, "plugin", "marketplace", "add", str(plugin_root)],
        [codex, "plugin", "add", plugin_name + "@" + marketplace],
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Show OS selection and commands; do not install anything")
    parser.add_argument("--codex", help="Path to a Codex CLI with plugin support")
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error("Python 3.11 or later is required")
    try:
        plugin_root, marketplace = edition(sys.platform)
    except ValueError as error:
        parser.error(str(error))
    codex = args.codex or shutil.which("codex")
    if not args.dry_run and not codex:
        parser.error("Codex CLI not found. Add it to PATH or supply --codex /path/to/codex")
    commands = plan(sys.platform, sys.executable, codex or "codex")
    print(json.dumps({"platform": sys.platform, "plugin_root": str(plugin_root),
                      "plugin": commands[-1][-1], "commands": commands}, indent=2), flush=True)
    if args.dry_run:
        return
    # Check CLI support before setup downloads dependencies or changes user config.
    subprocess.run([codex, "plugin", "add", "--help"], check=True, stdout=subprocess.DEVNULL)
    for command in commands:
        subprocess.run(command, check=True, cwd=plugin_root)
    print("Installed. Reopen Codex to load ArtCraft, then check craft_status and craft_engine_status.")


if __name__ == "__main__":
    main()
