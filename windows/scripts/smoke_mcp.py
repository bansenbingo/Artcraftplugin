#!/usr/bin/env python3
"""Exercise real MCP servers and installed Craft apps using synthetic documents only."""
import argparse
import asyncio
import base64
import json
import os
import socket
import signal
from datetime import datetime
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "servers"))
from craft_runtime import Runtime


async def main(live):
    runtime = Runtime()
    output = runtime.work / ("smoke-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    output.mkdir()
    isolated_config = json.loads(json.dumps(runtime.config))
    isolated_config["workspace"] = str(output)
    isolated_apps = isolated_config.setdefault("apps", {})
    private = output / ".control"
    private.mkdir(mode=0o700)
    for app in runtime.locks:
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            isolated_apps.setdefault(app, {})["port"] = reservation.getsockname()[1]
    isolated_apps["photocraft"]["token_file"] = str(private / "photo.token")
    isolated_apps["pdfcraft"]["control_file"] = str(private / "pdf.json")
    config_path = private / "config.json"
    config_path.write_text(json.dumps(isolated_config))
    config_path.chmod(0o600)
    child_env = dict(os.environ, CRAFT_AGENT_CONFIG=str(config_path))
    launched_pids = {}
    receipts = []
    for mode in ["desktop", "engine"]:
        if os.name == "nt":
            params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "servers/run.py"), mode], env=child_env)
        else:
            params = StdioServerParameters(command="sh", args=[str(ROOT / "servers/run.sh"), mode], env=child_env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = [t.name for t in (await session.list_tools()).tools]
                assert len(names) == (7 if mode == "desktop" else 4)

                async def call(name, **args):
                    reply = await session.call_tool(name, args)
                    if getattr(reply, "is_error", getattr(reply, "isError", False)):
                        raise RuntimeError(str(reply.content))
                    return reply

                status = await call("craft_status" if mode == "desktop" else "craft_engine_status")
                structured = getattr(status, "structured_content", getattr(status, "structuredContent", None))
                assert len(structured["apps"]) == 12
                invalid = await session.call_tool(names[0], {"unknown": True})
                assert getattr(invalid, "is_error", getattr(invalid, "isError", False))
                receipts.append({"mode": mode, "mcp_initialize": True, "tools": names, "strict_input_validation": True})
                if mode == "desktop" and live:
                    plans = {
                        "gridcraft": [("cell.set", {"cell": "A1", "input": "2"}), ("cell.set", {"cell": "A2", "input": "3"}), ("cell.set", {"cell": "A3", "input": "=SUM(A1:A2)"}), ("file.save", {"path": str(output / "agent-sheet.xlsx")})],
                        "wordcraft": [("text.insert", {"text": "Craft Agent 本地控制验证\n通过 MCP 写入并保存。"}), ("file.saveAs", {"path": str(output / "agent-document.docx")})],
                        "photocraft": [("file.new", {"width": 320, "height": 180, "background": "#3264a0", "name": "Agent Test"}), ("@app.save", {"path": str(output / "agent-image.psd")})],
                        "vectorcraft": [("file.new", {"width": 320, "height": 180, "units": "Points", "name": "Agent Test"}), ("shape.rectangle", {"x": 20, "y": 20, "width": 100, "height": 70}), ("file.save", {"path": str(output / "agent-vector.svg")})],
                        "effectcraft": [("comp.new", {"name": "Agent Test", "width": 320, "height": 180, "duration": 1, "frameRate": 24}), ("layer.newText", {"text": "Agent MCP", "size": 36}), ("file.saveAs", {"path": str(output / "agent-comp.ecproj")})],
                        "filmcraft": [("file.newProject", {"name": "Agent Test"}), ("file.newSequence", {"name": "Agent Sequence", "width": 320, "height": 180, "fps": 24}), ("file.saveAs", {"path": str(output / "agent-film.fcproj")})],
                        "deckcraft": [("file.new", {"blank": True}), ("slide.new", {"title": "Agent MCP", "body": "本地控制验证"}), ("file.save", {"path": str(output / "agent-deck.pptx")})],
                        "lightcraft": [("develop.set", {"control": "light.exposure", "value": 0.7})],
                        "pdfcraft": [("create.blank", {})],
                    }
                    installed = {a["app"] for a in status.structuredContent["apps"] if a["installed"]}
                    for app, steps in plans.items():
                        if app not in installed:
                            continue
                        launched = await call("craft_launch", app=app, scratch=True)
                        if launched.structuredContent.get("pid"):
                            launched_pids[app] = launched.structuredContent["pid"]
                        for command, arguments in steps:
                            if command.startswith("@"):
                                await call("craft_control", app=app, method=command[1:], params=arguments)
                                continue
                            found = await call("craft_list_commands", app=app, query=command, limit=100)
                            assert any(x["id"] == command and x["enabled"] for x in found.structuredContent["items"]), (app, command)
                            await call("craft_command", app=app, command=command, params=arguments)
                        state = await call("craft_inspect", app=app)
                        if app == "gridcraft":
                            cell = await call("craft_control", app=app, method="cell.get", params={"cell": "A3"})
                            assert "5" in json.dumps(cell.structuredContent), cell
                        image = await call("craft_screenshot", app=app)
                        block = next(c for c in image.content if c.type == "image")
                        png = base64.b64decode(block.data)
                        assert png.startswith(b"\x89PNG\r\n\x1a\n")
                        (output / (app + "-window.png")).write_bytes(png)
                        receipt = {"app": app, "desktop_edit": True, "inspect": True, "window_png_bytes": len(png)}
                        receipts.append(receipt)
                        print(json.dumps(receipt), flush=True)
                    # Close only the isolated synthetic instances created by this run.
                    for app in plans:
                        if app in installed:
                            try:
                                await call("craft_control", app=app, method="ui.quit" if app == "pdfcraft" else "app.quit")
                            except RuntimeError:
                                # Older PdfCraft has no quit control method. Only this run's
                                # synthetic process may be terminated, never an attached window.
                                pid = launched_pids.get(app)
                                if pid:
                                    try:
                                        os.kill(pid, signal.SIGTERM)
                                    except ProcessLookupError:
                                        pass
                if mode == "engine" and runtime.executable("gridcraft", cli=True):
                    discovery = await call("craft_engine_tools", app="gridcraft", query="command", limit=100)
                    assert any(t["name"] == "execute_command" for t in discovery.structuredContent["items"])
                    for cell, value in [("B1", "7"), ("B2", "11"), ("B3", "=SUM(B1:B2)")]:
                        await call("craft_engine_call", app="gridcraft", tool="set_cell", arguments={"cell": cell, "input": value})
                    check = await call("craft_engine_call", app="gridcraft", tool="get_cell", arguments={"cell": "B3"})
                    assert "18" in str(check), check
                    await call("craft_engine_call", app="gridcraft", tool="save_workbook", arguments={"path": str(output / "headless-sheet.xlsx")})
                    bad = await session.call_tool("craft_engine_call", {"app": "gridcraft", "tool": "does_not_exist", "arguments": {}})
                    assert getattr(bad, "is_error", getattr(bad, "isError", False))
                    receipts.append({"app": "gridcraft", "native_mcp": True, "persistent_formula_result": 18, "save": True, "unknown_tool_rejected": True})
                if mode == "engine" and runtime.executable("lightcraft", cli=True):
                    # Synthetic PNG from the PhotoCraft smoke output, or a previously generated one.
                    source = output / "photocraft-window.png"
                    if source.exists():
                        await call("craft_engine_tools", app="lightcraft", query="set_develop")
                        await call("craft_engine_call", app="lightcraft", tool="import", arguments={"paths": [str(source)]})
                        await call("craft_engine_call", app="lightcraft", tool="set_develop", arguments={"values": {"light.exposure": 0.5}})
                        preview = await call("craft_engine_call", app="lightcraft", tool="render_photo", arguments={"size": 256})
                        image = next(c for c in preview.content if c.type == "image")
                        assert base64.b64decode(image.data).startswith(b"\x89PNG")
                        await call("craft_engine_call", app="lightcraft", tool="export", arguments={"path": str(output / "headless-photo.png"), "longEdge": 256, "format": "png"})
                        receipts.append({"app": "lightcraft", "native_mcp": True, "develop_edit": True, "native_image_forwarded": True, "export": True})
    for file in output.glob("*.*"):
        if file.is_file():
            assert file.stat().st_size > 0
    report = {"output": str(output), "receipts": receipts}
    (ROOT / "test-results").mkdir(exist_ok=True)
    name = "smoke-live.json" if live else "smoke-protocol.json"
    (ROOT / "test-results" / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Also create synthetic documents in installed GUI apps")
    args = parser.parse_args()
    asyncio.run(main(args.live))
