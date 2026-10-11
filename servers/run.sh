#!/bin/sh
set -eu
task_plugin_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
task_runtime_dir=${CRAFT_AGENT_HOME:-"$HOME/.local/share/artcraft-agent"}
task_python="$task_runtime_dir/venv/bin/python"
if [ ! -x "$task_python" ]; then
  echo "ArtCraft Agent runtime missing. Run: python3 $task_plugin_root/scripts/setup.py" >&2
  exit 1
fi
exec "$task_python" "$task_plugin_root/servers/craft_mcp.py" "$@"
