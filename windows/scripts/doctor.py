#!/usr/bin/env python3
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "servers"))
from craft_runtime import Runtime
print(json.dumps(Runtime().status(), ensure_ascii=False, indent=2))
