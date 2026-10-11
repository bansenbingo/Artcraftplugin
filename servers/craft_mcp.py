"""Two local MCP servers: live desktop control and persistent headless engines."""
from __future__ import annotations

import asyncio
import base64
import json
import sys
from typing import Any, Literal

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from pydantic import BaseModel, ConfigDict, Field

from craft_runtime import APPS, CraftError, NativeSession, Runtime

App = Literal["photocraft", "vectorcraft", "filmcraft", "lightcraft", "pdfcraft", "effectcraft", "designcraft", "wordcraft", "gridcraft", "deckcraft", "soundcraft", "cadcraft"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppInput(Input):
    app: App = Field(description="Craft application id")


class Launch(AppInput):
    scratch: bool = Field(default=False, description="Use temporary preferences where supported; LightCraft uses an in-memory demo library")


class Inspect(AppInput):
    view: Literal["document", "ui"] = Field(default="document", description="Document summary or live UI state")


class Search(AppInput):
    query: str = Field(default="", max_length=200, description="Case-insensitive substring in the command/tool definition")
    offset: int = Field(default=0, ge=0, description="Index of the first match")
    limit: int = Field(default=30, ge=1, le=100, description="Maximum matches returned")


class Command(AppInput):
    command: str = Field(min_length=1, max_length=256, description="Exact id discovered from craft_list_commands")
    params: dict[str, Any] = Field(default_factory=dict, description="Engine-defined JSON parameters; consult the discovered command description")


class Control(AppInput):
    method: str = Field(min_length=1, max_length=256, description="Exact control method from the app's control-protocol documentation; e.g. ui.key or ui.inspect")
    params: dict[str, Any] = Field(default_factory=dict, description="Method-specific JSON parameters")


class NativeCall(AppInput):
    tool: str = Field(min_length=1, max_length=256, description="Exact native MCP tool name from craft_engine_tools")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Arguments validated against the native tool's inputSchema")
    timeout_seconds: int = Field(default=300, ge=1, le=3600, description="Deadline for this native call; a timeout does not cancel editing/rendering")


class Reset(AppInput):
    discard_unsaved: Literal[True] = Field(description="Explicitly acknowledge that unsaved in-memory headless state will be discarded")


def result(value: Any) -> types.CallToolResult:
    structured = value if isinstance(value, dict) else {"result": value}
    return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(structured, ensure_ascii=False))], structuredContent=structured)


def definition(name: str, model: type[Input], description: str, read_only: bool = False, destructive: bool = True) -> types.Tool:
    return types.Tool(name=name, title=name.replace("_", " ").title(), description=description, inputSchema=model.model_json_schema(), annotations=types.ToolAnnotations(readOnlyHint=read_only, destructiveHint=destructive, idempotentHint=read_only, openWorldHint=False))


def build_server(mode: str, runtime: Runtime | None = None):
    runtime = runtime or Runtime()
    sessions: dict[str, NativeSession] = {}
    server = Server("craft-desktop" if mode == "desktop" else "craft-engine", version="0.1.0", instructions=(
        "Control the user's local Craft apps. Desktop mode edits the live window; engine mode is a separate in-memory document. Discover commands/tools before using them. Save native project and exports explicitly. On timeout inspect state before retrying an edit."
    ))
    if mode == "desktop":
        catalog = [
            definition("craft_status", Input, "Discover installed Craft GUI/CLI executables, versions, workspace and configured local control ports. Port openness alone is not application verification.", True, False),
            definition("craft_launch", Launch, "Launch an installed Craft GUI with its local control channel, or reuse a verified endpoint. Returns readiness; never kills an existing app. PhotoCraft/VectorCraft access the configured workspace; other apps have their native permissions.", False, False),
            definition("craft_list_commands", Search, "Discover the live app's command ids, parameter descriptions and enablement; paginated substring search.", True, False),
            definition("craft_inspect", Inspect, "Read the current live document/library summary or UI state. This does not open a new document.", True, False),
            definition("craft_command", Command, "Run a discovered command against the actual desktop document. May edit, save, export or overwrite files. PdfCraft live commands take an id only; use its raw UI controls or native task tools for parameters."),
            definition("craft_control", Control, "Send an app-specific JSON control method, including UI input, file operations or application control. Discover methods from source references; this is not MCP-over-TCP."),
            definition("craft_screenshot", AppInput, "Capture the actual app window and return MCP PNG image content. Also saves a unique PNG in the configured workspace when supported; the window must be drawing frames.", False, False),
        ]
    else:
        catalog = [
            definition("craft_engine_status", Input, "Discover local native Craft CLIs. Missing CLIs do not prevent this MCP server from starting. Does not start any engine.", True, False),
            definition("craft_engine_tools", Search, "Start/reuse a persistent headless native MCP session and discover its tools with exact input schemas. This is a different document from the GUI. May initialize native settings.", False, False),
            definition("craft_engine_call", NativeCall, "Call a discovered native MCP tool in a persistent headless engine. Preserves native image content, structured results and errors. May edit/save/export/overwrite local files. Progress/cancellation are not forwarded by this bridge."),
            definition("craft_engine_reset", Reset, "Close and discard this app's headless session. Unsaved in-memory work is lost. Next call starts a new empty/default session."),
        ]
    models = {
        "craft_status": Input, "craft_launch": Launch, "craft_list_commands": Search,
        "craft_inspect": Inspect, "craft_command": Command, "craft_control": Control,
        "craft_screenshot": AppInput, "craft_engine_status": Input,
        "craft_engine_tools": Search, "craft_engine_call": NativeCall, "craft_engine_reset": Reset,
    }

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return catalog

    def invoke(name: str, arguments: dict) -> types.CallToolResult:
        if name not in {t.name for t in catalog}:
            raise CraftError(f"Unknown tool {name}")
        data = models[name].model_validate(arguments).model_dump()
        if name in {"craft_status", "craft_engine_status"}:
            return result(runtime.status())
        app = data.pop("app")
        if name == "craft_launch":
            return result(runtime.launch(app, **data))
        if name == "craft_list_commands":
            return result(runtime.commands(app, **data))
        if name == "craft_inspect":
            return result(runtime.inspect(app, **data))
        if name == "craft_command":
            return result(runtime.command(app, **data))
        if name == "craft_control":
            return result(runtime.control(app, **data))
        if name == "craft_screenshot":
            png, metadata = runtime.screenshot(app)
            return types.CallToolResult(content=[types.ImageContent(type="image", data=base64.b64encode(png).decode(), mimeType="image/png"), types.TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False))], structuredContent=metadata)
        session = sessions.setdefault(app, NativeSession(runtime, app))
        if name == "craft_engine_tools":
            tools = session.tools()
            items = [t for t in tools if not data["query"] or data["query"].casefold() in json.dumps(t, ensure_ascii=False).casefold()]
            end = data["offset"] + data["limit"]
            return result({"items": items[data["offset"]:end], "total_count": len(items), "has_more": end < len(items), "next_offset": end if end < len(items) else None})
        if name == "craft_engine_call":
            raw = session.call(data["tool"], data["arguments"], data["timeout_seconds"])
            return types.CallToolResult.model_validate(raw)
        session.close()
        sessions.pop(app, None)
        return result({"app": app, "headless_session_closed": True})

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> types.CallToolResult:
        try:
            return await asyncio.to_thread(invoke, name, arguments)
        except Exception as exc:
            return types.CallToolResult(isError=True, content=[types.TextContent(type="text", text=f"{type(exc).__name__}: {exc}")])

    return server, sessions


async def main(mode: str):
    server, sessions = build_server(mode)
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        for session in list(sessions.values()):
            session.close()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"desktop", "engine"}:
        raise SystemExit("usage: craft_mcp.py desktop|engine")
    asyncio.run(main(sys.argv[1]))
