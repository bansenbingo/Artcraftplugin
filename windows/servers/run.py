"""Cross-platform launcher for the ArtCraft MCP servers."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def runtime_python() -> Path:
    configured = os.environ.get("CRAFT_AGENT_PYTHON")
    if configured:
        return Path(configured).expanduser()
    configured_home = os.environ.get("CRAFT_AGENT_HOME")
    home = Path(configured_home).expanduser() if configured_home else ((Path(os.environ["LOCALAPPDATA"]) / "artcraft-agent") if os.name == "nt" and os.environ.get("LOCALAPPDATA") else Path.home() / ".local" / "share" / "artcraft-agent")
    candidate = home / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return candidate


def main() -> int:
    target = runtime_python()
    if target.resolve() != Path(sys.executable).resolve() and target.is_file():
        return subprocess.call([str(target), str(ROOT / "servers" / "craft_mcp.py"), *sys.argv[1:]])
    if target.resolve() != Path(sys.executable).resolve() and not target.is_file():
        print(f"ArtCraft Agent runtime missing: {target}. Run: {sys.executable} {ROOT / 'scripts' / 'setup.py'}", file=sys.stderr)
        return 1
    os.execv(sys.executable, [sys.executable, str(ROOT / "servers" / "craft_mcp.py"), *sys.argv[1:]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
