#!/usr/bin/env python3
"""Install the local runtime; optionally install official, checksum-verified macOS CLIs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "servers"))
from craft_runtime import APPS, Runtime


def install_cli(app: str, version: str | None, runtime: Runtime):
    if sys.platform != "darwin":
        raise SystemExit("Automatic CLI download currently supports macOS. Set apps.<app>.cli to a built/installed CLI on Windows/Linux")
    if app not in APPS:
        raise SystemExit(f"Unknown app: {app}")
    if not version:
        exe = runtime.executable(app)
        if not exe or ".app/Contents/MacOS/" not in exe:
            raise SystemExit(f"Install {APPS[app]} first, or give --version")
        with (Path(exe).parent.parent / "Info.plist").open("rb") as f:
            version = plistlib.load(f)["CFBundleShortVersionString"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?", version):
        raise SystemExit("Invalid release version")
    base = f"https://github.com/storytold/{app}/releases/download/v{version}/"
    asset = f"{app}-cli-{version}-macos-universal.zip"
    with tempfile.TemporaryDirectory(prefix="craft-cli-") as temp:
        stage = Path(temp)
        for name in ["SHA256SUMS.txt", asset]:
            subprocess.run(["curl", "--fail", "--location", "--retry", "3", "--connect-timeout", "20", "--max-time", "600", "--output", str(stage / name), base + name], check=True)
        sums = {}
        for line in (stage / "SHA256SUMS.txt").read_text().splitlines():
            if len(line.split()) == 2:
                digest, name = line.split()
                sums[name.lstrip("*")] = digest
        with (stage / asset).open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if sums.get(asset) != digest:
            raise SystemExit("Official checksum verification failed; nothing installed")
        unpack = stage / "unpack"
        unpack.mkdir()
        with zipfile.ZipFile(stage / asset) as archive:
            for member in archive.infolist():
                target = (unpack / member.filename).resolve()
                if not target.is_relative_to(unpack.resolve()) or (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise SystemExit("Unsafe archive member; nothing installed")
            archive.extractall(unpack)
        binaries = list(unpack.rglob(app + "-cli"))
        if len(binaries) != 1:
            raise SystemExit("Expected exactly one CLI in the official archive")
        binary_rel = binaries[0].relative_to(unpack)
        dest = runtime.home / "bin" / app / version
        if dest.exists():
            raise SystemExit(f"Version already installed at {dest}; update config manually if needed")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(unpack, dest)
        binary = dest / binary_rel
        binary.chmod(0o755)
        config = json.loads(runtime.config_path.read_text(encoding="utf-8-sig")) if runtime.config_path.exists() else {"workspace": str(runtime.work), "apps": {}}
        config.setdefault("apps", {}).setdefault(app, {})["cli"] = str(binary)
        runtime.config_path.parent.mkdir(parents=True, exist_ok=True)
        runtime.config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        runtime.config_path.chmod(0o600)
        receipt = {"app": app, "version": version, "url": base + asset, "sha256": digest, "binary": str(binary)}
        (dest / "install-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-cli", choices=list(APPS))
    parser.add_argument("--version")
    parser.add_argument("--skip-runtime", action="store_true")
    args = parser.parse_args()
    runtime = Runtime()
    if not args.skip_runtime:
        venv = runtime.home / "venv"
        python_name = "Scripts/python.exe" if os.name == "nt" else "bin/python"
        venv_python = venv / python_name
        if not venv_python.exists():
            subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(ROOT / "requirements-lock.txt")], check=True)
    if not runtime.config_path.exists():
        runtime.config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "config.example.json", runtime.config_path)
        runtime.config_path.chmod(0o600)
    if args.install_cli:
        install_cli(args.install_cli, args.version, runtime)
    print(f"Ready. Workspace: {runtime.work}; config: {runtime.config_path}")


if __name__ == "__main__":
    main()
