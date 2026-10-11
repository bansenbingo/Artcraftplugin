"""Local Craft protocols, kept independent of the MCP frontend."""
from __future__ import annotations

import base64
import json
import os
import plistlib
import queue
import select
import shutil
import socket
import stat
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

APPS = {
    "photocraft": "PhotoCraft", "vectorcraft": "VectorCraft",
    "filmcraft": "FilmCraft", "lightcraft": "LightCraft",
    "pdfcraft": "PdfCraft", "effectcraft": "EffectCraft",
    "designcraft": "DesignCraft", "wordcraft": "WordCraft",
    "gridcraft": "GridCraft", "deckcraft": "DeckCraft",
    "soundcraft": "SoundCraft", "cadcraft": "CADCraft",
}
DEFAULT_PORTS = {app: 19001 + i for i, app in enumerate(APPS)}
MAX_LINE = 64 * 1024 * 1024


class CraftError(RuntimeError):
    pass


def private_text(path: Path) -> str:
    """Read a credential without following a symlink or accepting a shared file."""
    if path.is_symlink():
        raise CraftError(f"Credential must not be a symlink: {path}")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise CraftError(f"Credential is not a regular file: {path}")
        if os.name == "posix" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise CraftError(f"Credential must be yours and mode 0600: {path}")
        value = stream.read(8193)
        if len(value) > 8192:
            raise CraftError(f"Credential file too large: {path}")
        return value.strip()


def decode_reply(reply: dict, expected: str) -> Any:
    if reply.get("id") != expected:
        raise CraftError("Unexpected response id; inspect state before retrying an edit")
    if "error" in reply:
        error = reply["error"]
        raise CraftError(error.get("message", str(error)) if isinstance(error, dict) else str(error))
    if reply.get("ok") is False:
        raise CraftError(str(reply.get("error", "Craft command failed")))
    return reply.get("result")


class Runtime:
    def __init__(self, config_path: Path | None = None):
        default_home = (Path(os.environ["LOCALAPPDATA"]) / "artcraft-agent" if os.name == "nt" and os.environ.get("LOCALAPPDATA") else Path.home() / ".local" / "share" / "artcraft-agent")
        default_config = (Path(os.environ["APPDATA"]) / "artcraft-agent" / "config.json" if os.name == "nt" and os.environ.get("APPDATA") else Path.home() / ".config" / "artcraft-agent" / "config.json")
        self.home = Path(os.environ.get("CRAFT_AGENT_HOME", str(default_home))).expanduser().resolve()
        self.config_path = config_path or Path(os.environ.get("CRAFT_AGENT_CONFIG", str(default_config))).expanduser()
        self.config = json.loads(self.config_path.read_text(encoding="utf-8-sig")) if self.config_path.exists() else {}
        self.work = Path(self.config.get("workspace", "~/Documents/CraftAgent")).expanduser().resolve()
        self.run_dir = self.home / "run"
        self.run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.run_dir.chmod(0o700)
        self.work.mkdir(parents=True, exist_ok=True)
        self.locks = {app: threading.RLock() for app in APPS}
        self.processes: dict[str, subprocess.Popen] = {}

    def settings(self, app: str) -> dict:
        if app not in APPS:
            raise CraftError(f"Unknown app {app!r}; choose one of {', '.join(APPS)}")
        return self.config.get("apps", {}).get(app, {})

    def executable(self, app: str, cli: bool = False) -> str | None:
        cfg = self.settings(app)
        override = cfg.get("cli" if cli else "executable")
        if override:
            path = Path(override).expanduser().resolve()
            if not path.is_file() or not os.access(path, os.X_OK):
                raise CraftError(f"Configured executable is missing or not executable: {path}")
            return str(path)
        label = APPS[app]
        if cli:
            names = [app + "-cli", app + "-cli.exe"] if os.name == "nt" else [app + "-cli"]
            folders = [self.home / "bin", Path.home() / ".local/bin"]
            if os.name != "nt":
                folders += [Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
            else:
                folders += [Path(root) / APPS[app] for root in [os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432"), os.environ.get("LOCALAPPDATA")] if root]
            for folder in folders:
                for name in names:
                    path = folder / name
                    if path.is_file() and (os.name == "nt" or os.access(path, os.X_OK)):
                        return str(path)
            return shutil.which(app + ("-cli.exe" if os.name == "nt" else "-cli"))
        if os.name == "nt":
            candidates = []
            for root in [os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432"), os.environ.get("LOCALAPPDATA")]:
                if root:
                    candidates += [Path(root) / label / (label + ".exe"), Path(root) / (label + ".exe"), Path(root) / (app + ".exe")]
            candidates += [Path(self.home) / "bin" / (label + ".exe"), Path(self.home) / "bin" / (app + ".exe")]
            for path in candidates:
                if path.is_file():
                    return str(path.resolve())
            return shutil.which(label) or shutil.which(app)
        for folder in [Path("/Applications"), Path.home() / "Applications"]:
            path = folder / (label + ".app") / "Contents/MacOS" / label
            if path.is_file():
                return str(path)
        return shutil.which(app)

    def endpoint(self, app: str) -> tuple[int, tuple[str, str] | None]:
        cfg = self.settings(app)
        if app == "pdfcraft":
            path = Path(cfg.get("control_file", str(self.run_dir / "pdfcraft-control.json"))).expanduser()
            info = json.loads(private_text(path))
            port, auth = info["port"], ("token", info["token"])
        else:
            port = cfg.get("port", DEFAULT_PORTS[app])
            auth = None
            if app == "photocraft":
                path = Path(cfg.get("token_file", str(self.run_dir / "photocraft.token"))).expanduser()
                auth = ("token", private_text(path))
            elif app == "wordcraft":
                default = Path.home() / "Library/Application Support/WordCraft" / f"control-key.local-{port}"
                path = Path(cfg.get("key_file", str(default))).expanduser()
                auth = ("key", private_text(path))
        if type(port) is not int or not 1 <= port <= 65535:
            raise CraftError("Control port must be an integer between 1 and 65535")
        return port, auth

    def control(self, app: str, method: str, params: dict | None = None, timeout: float = 65) -> Any:
        self.settings(app)
        with self.locks[app]:
            port, auth = self.endpoint(app)
            sent = False
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=min(timeout, 5)) as conn:
                    conn.settimeout(timeout)
                    with conn.makefile("rb") as reader:
                        def request(name: str, arguments: dict) -> Any:
                            nonlocal sent
                            rid = uuid.uuid4().hex
                            wire = {"jsonrpc": "2.0", "id": rid, "method": name, "params": arguments}
                            encoded = (json.dumps(wire, ensure_ascii=False) + "\n").encode()
                            if len(encoded) > 1024 * 1024:
                                raise CraftError("Control request exceeds 1 MiB; split this operation")
                            if name != "auth":
                                sent = True
                            conn.sendall(encoded)
                            line = reader.readline(MAX_LINE + 1)
                            if not line or len(line) > MAX_LINE:
                                raise CraftError("Missing or oversized reply; operation may have completed. Inspect state before retrying")
                            return decode_reply(json.loads(line), rid)
                        if auth:
                            request("auth", {auth[0]: auth[1]})
                        return request(method, params or {})
            except (OSError, ValueError) as exc:
                suffix = "Operation may have completed; inspect state before retrying." if sent else "Use craft_launch, or configure the running app's control endpoint."
                raise CraftError(f"{APPS[app]} control failed ({type(exc).__name__}). {suffix}") from exc

    def command(self, app: str, command: str, params: dict | None = None) -> Any:
        if app == "pdfcraft":
            if params:
                raise CraftError("PdfCraft's live ui.command accepts only an id. Use craft_control for ui.open/ui.set/dialog input, or craft-engine for PDF task tools")
            return self.control(app, "ui.command", {"id": command})
        return self.control(app, "engine.execute", {"command": command, "params": params or {}})

    def inspect(self, app: str, view: str = "document") -> Any:
        if view == "ui":
            return self.control(app, "ui.state" if app == "pdfcraft" else "ui.inspect")
        if app == "pdfcraft":
            return self.control(app, "ui.state")
        if app == "photocraft":
            return self.command(app, "document.inspect")
        if app == "filmcraft":
            return self.command(app, "project.inspect")
        if app == "effectcraft":
            return self.command(app, "project.summary")
        if app == "lightcraft":
            return self.command(app, "library.state")
        return self.control(app, "session.inspect" if app == "soundcraft" else "document.inspect")

    def commands(self, app: str, query: str = "", offset: int = 0, limit: int = 30) -> dict:
        data = self.control(app, "ui.commands" if app == "pdfcraft" else "engine.commands")
        if isinstance(data, dict):
            data = data.get("commands", data.get("items", []))
        if not isinstance(data, list):
            raise CraftError("Unexpected command catalog; inspect this app's protocol/version")
        terms = query.casefold()
        items = [x for x in data if not terms or terms in json.dumps(x, ensure_ascii=False).casefold()]
        end = offset + limit
        return {"items": items[offset:end], "total_count": len(items), "has_more": end < len(items), "next_offset": end if end < len(items) else None}

    def status(self) -> dict:
        items = []
        for app, label in APPS.items():
            exe, cli = self.executable(app), self.executable(app, cli=True)
            version = None
            if exe and ".app/Contents/MacOS/" in exe:
                plist = Path(exe).parent.parent / "Info.plist"
                with plist.open("rb") as f:
                    version = plistlib.load(f).get("CFBundleShortVersionString")
            port = self.settings(app).get("port", DEFAULT_PORTS[app])
            if app == "pdfcraft":
                try:
                    port, _ = self.endpoint(app)
                except (OSError, ValueError, KeyError, CraftError):
                    port = None
            listening = False
            if port:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                        listening = True
                except OSError:
                    pass
            items.append({"app": app, "installed": bool(exe), "version": version, "executable": exe, "cli": cli, "port": port, "port_open_unverified": listening})
        return {"platform": os.sys.platform, "config": str(self.config_path), "workspace": str(self.work), "apps": items}

    def launch(self, app: str, scratch: bool = False) -> dict:
        with self.locks[app]:
            cfg = self.settings(app)
            exe = self.executable(app)
            if not exe:
                raise CraftError(f"Install {APPS[app]} from https://github.com/storytold/{app}/releases first")
            try:
                self.inspect(app, "ui")
                return {"app": app, "already_running": True}
            except (CraftError, OSError, KeyError, ValueError):
                pass
            previous = self.processes.get(app)
            if previous is not None and previous.poll() is None:
                raise CraftError(f"{APPS[app]} was already launched (pid {previous.pid}) but is not answering. Inspect its log before launching another instance")
            port = cfg.get("port", DEFAULT_PORTS[app])
            if app != "pdfcraft":
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        raise CraftError(f"Port {port} is occupied but this app could not be verified. Configure a different port; existing processes were left running")
                except OSError:
                    pass
            args = [exe, "--control", str(port)]
            env = os.environ.copy()
            if app == "photocraft":
                token = Path(cfg.get("token_file", str(self.run_dir / "photocraft.token"))).expanduser()
                args += ["--control-token-file", str(token)]
            if app in {"photocraft", "vectorcraft"}:
                args += ["--automation-read-root", str(self.work), "--automation-write-root", str(self.work)]
            if app == "pdfcraft":
                path = Path(cfg.get("control_file", str(self.run_dir / "pdfcraft-control.json"))).expanduser()
                if path.exists():
                    old_port, _ = self.endpoint(app)
                    try:
                        with socket.create_connection(("127.0.0.1", old_port), timeout=0.2):
                            raise CraftError("PdfCraft control file points to an unverified live process; choose a new control_file")
                    except OSError:
                        path.unlink()
                args = [exe, "--control", str(path)]
            if app == "lightcraft":
                args += ["--memory"] if scratch else ["--library", str(Path(cfg.get("library", str(self.work / "LightCraft Library"))).expanduser()), "--no-demo"]
            if app == "effectcraft" and scratch:
                args += ["--empty"]
            if app == "soundcraft":
                args += ["--no-audio"]
            if scratch:
                profile = self.run_dir / (app + "-profile")
                profile.mkdir(exist_ok=True)
                if app in {"photocraft", "vectorcraft", "effectcraft", "lightcraft", "soundcraft"}:
                    env[app.upper() + "_CONFIG_DIR"] = str(profile)
                elif app in {"wordcraft", "gridcraft"}:
                    env[app.upper() + "_NO_PREFS"] = "1"
            with (self.run_dir / (app + ".log")).open("ab") as log:
                proc = subprocess.Popen(args, cwd=self.work, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            self.processes[app] = proc
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise CraftError(f"{APPS[app]} exited ({proc.returncode}); see {self.run_dir / (app + '.log')}")
                try:
                    self.inspect(app, "ui")
                    return {"app": app, "pid": proc.pid, "scratch": scratch, "workspace": str(self.work)}
                except (CraftError, OSError, KeyError, ValueError):
                    time.sleep(0.2)
            raise CraftError(f"{APPS[app]} launched (pid {proc.pid}) but control is not ready; see {self.run_dir / (app + '.log')}. No second instance was started")

    def screenshot(self, app: str) -> tuple[bytes, dict]:
        params = {}
        if app != "pdfcraft":
            params["path"] = str(self.work / ("agent-" + app + "-" + uuid.uuid4().hex[:8] + ".png"))
        reply = self.control(app, "ui.screenshot", params)
        for key in ["png", "png_base64", "base64", "data"]:
            if isinstance(reply.get(key), str):
                return base64.b64decode(reply[key], validate=True), {k: v for k, v in reply.items() if k != key}
        if reply.get("path"):
            path = Path(reply["path"]).resolve()
            if not path.is_relative_to(self.work):
                raise CraftError("Screenshot path escaped the configured workspace")
            if path.stat().st_size > MAX_LINE:
                raise CraftError("Screenshot exceeds 64 MiB; resize the app window")
            return path.read_bytes(), reply
        raise CraftError("No PNG returned; inspect the app's screenshot response/version")


class NativeSession:
    """Persistent stdio child, preserving the editor's in-memory document across calls."""
    def __init__(self, runtime: Runtime, app: str):
        self.runtime, self.app = runtime, app
        self.lock = threading.RLock()
        self.proc: subprocess.Popen | None = None
        self.buffer = b""
        self.progress = None
        self._reader_queue: queue.Queue[bytes | None] = queue.Queue()

    def start(self):
        if self.proc is not None:
            if self.proc.poll() is not None:
                raise CraftError("Native engine exited. Its unsaved in-memory state may be lost; use craft_engine_reset only when ready to start a new session")
            return
        exe = self.runtime.executable(self.app, cli=True)
        if not exe:
            raise CraftError(f"Missing {self.app}-cli. Install the matching official CLI release or cargo build --release -p {self.app}-cli, then set apps.{self.app}.cli in {self.runtime.config_path}")
        args = [exe, "mcp"]
        if os.name == "nt" and Path(exe).suffix.lower() not in {".exe", ".com", ".bat", ".cmd"}:
            args = [sys.executable, exe, "mcp"]
        if self.app == "vectorcraft":
            args += ["--headless"]
        if self.app in {"photocraft", "vectorcraft", "effectcraft"}:
            args += ["--automation-read-root", str(self.runtime.work), "--automation-write-root", str(self.runtime.work)]
        if self.app == "pdfcraft":
            args += ["--root", str(self.runtime.work)]
        extra = self.runtime.settings(self.app).get("headless_args", [])
        if not isinstance(extra, list) or any(not isinstance(x, str) for x in extra):
            raise CraftError("headless_args must be a JSON array of strings")
        if any(x.split("=")[0] in {"--connect", "--bridge"} for x in extra):
            raise CraftError("craft-engine is headless; use craft-desktop for live control")
        args += extra
        with (self.runtime.run_dir / (self.app + "-engine.log")).open("ab") as log:
            self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, cwd=self.runtime.work)
        if os.name == "nt":
            threading.Thread(target=self._read_windows, daemon=True).start()
        try:
            self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "artcraft-agent", "version": "0.1.0"}}, 30)
            self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except Exception:
            self.close()
            raise

    def send(self, message: dict):
        self.proc.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode())
        self.proc.stdin.flush()

    def _read_windows(self):
        try:
            for line in iter(self.proc.stdout.readline, b""):
                self._reader_queue.put(line)
        finally:
            self._reader_queue.put(None)

    def rpc(self, method: str, params: dict, timeout: float = 300) -> Any:
        rid = uuid.uuid4().hex
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if os.name == "nt":
                try:
                    line = self._reader_queue.get(timeout=max(0, deadline - time.monotonic()))
                except queue.Empty:
                    break
                if line is None:
                    raise CraftError("Native engine closed stdout; inspect its engine log. Unsaved state may be lost")
                reply = json.loads(line)
                if reply.get("method") == "notifications/progress":
                    self.progress = reply.get("params")
                    continue
                if "method" in reply:
                    if "id" in reply:
                        self.send({"jsonrpc": "2.0", "id": reply["id"], "error": {"code": -32601, "message": "Server-to-client requests are not supported by this bridge"}})
                    continue
                if reply.get("id") != rid:
                    continue
                return decode_reply(reply, rid)
            if b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                reply = json.loads(line)
                if reply.get("method") == "notifications/progress":
                    self.progress = reply.get("params")
                    continue
                if "method" in reply:
                    if "id" in reply:
                        self.send({"jsonrpc": "2.0", "id": reply["id"], "error": {"code": -32601, "message": "Server-to-client requests are not supported by this bridge"}})
                    continue
                if reply.get("id") != rid:
                    # A previous timed-out operation may reply later. Never replay it.
                    continue
                return decode_reply(reply, rid)
            ready, _, _ = select.select([self.proc.stdout], [], [], max(0, deadline - time.monotonic()))
            if ready:
                data = os.read(self.proc.stdout.fileno(), 65536)
                if not data:
                    raise CraftError("Native engine closed stdout; inspect its engine log. Unsaved state may be lost")
                self.buffer += data
                if len(self.buffer) > MAX_LINE:
                    raise CraftError("Native reply exceeds 64 MiB; use smaller previews or focused queries")
        raise CraftError("Native request timed out; operation may have completed. Inspect state before retrying. The engine was left running")

    def tools(self) -> list[dict]:
        with self.lock:
            self.start()
            tools, cursor = [], None
            while True:
                data = self.rpc("tools/list", {"cursor": cursor} if cursor else {})
                tools.extend(data.get("tools", []))
                cursor = data.get("nextCursor")
                if not cursor:
                    return tools

    def call(self, tool: str, arguments: dict, timeout: float = 300) -> dict:
        import jsonschema
        with self.lock:
            catalog = {t["name"]: t for t in self.tools()}
            if tool not in catalog:
                raise CraftError(f"Unknown native tool {tool!r}; discover it with craft_engine_tools")
            jsonschema.validate(arguments, catalog[tool].get("inputSchema", {}))
            return self.rpc("tools/call", {"name": tool, "arguments": arguments}, timeout)

    def close(self):
        with self.lock:
            if self.proc:
                self.proc.stdin.close()
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.proc.terminate()
                    try:
                        self.proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.proc.kill()
                        self.proc.wait()
                self.proc.stdout.close()
                self.proc = None
                self.buffer = b""
