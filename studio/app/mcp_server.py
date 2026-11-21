"""The studio as an MCP server, so AI agents can edit alongside the person.

Every operation in `ops` becomes a tool. Agents connect over HTTP:

    claude mcp add --transport http studio http://127.0.0.1:8765/mcp
"""
from __future__ import annotations

import json
import time

import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings

from . import config, model, ops, ops_jobs
from .jobs import UserError, jobs

ACTIVE = {"pid": None}   # the project open in the browser, used when a tool call names none

PROJECT = {"type": "string", "description": "Project id or name. Omit to use the project that is open in the studio."}

INSTRUCTIONS = """This is a video editing studio running on the user's own computer. The user usually has the \
project open in a browser and sees every edit you make immediately; every edit can be undone with the undo tool.

Start with get_project to see the tracks, items and timing, and get_transcript for the spoken words. \
The main video track plays its clips one after another with no gaps; other tracks hold items placed freely in time. \
Cutting speech is done by deleting words from the transcript (delete_words, delete_text) rather than by timing. \
Tools that take a while (transcribe, export, add_narration, add_stock) return a job id: call wait_for_job to get \
the result. Times are timeline seconds unless a parameter says otherwise."""

EXTRA = [
    types.Tool(name="list_projects", description="List the projects in the studio, most recently edited first.",
               input_schema={"type": "object", "properties": {}, "additionalProperties": False}),
    types.Tool(name="create_project", description="Create a new, empty project. Add media with import_media.",
               input_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"],
                             "additionalProperties": False}),
    types.Tool(name="wait_for_job", description="Wait for a background job to finish (up to `timeout` seconds, "
                                                "default 60) and return its result or its progress so far.",
               input_schema={"type": "object", "properties": {"job": {"type": "string"}, "timeout": {"type": "number"}},
                             "required": ["job"], "additionalProperties": False}),
]


def tools() -> list[types.Tool]:
    out = list(EXTRA)
    for spec in ops.OPS.values():
        schema = spec.schema()
        schema["properties"] = {"project": PROJECT, **schema["properties"]}
        out.append(types.Tool(name=spec.name, description=spec.desc, input_schema=schema))
    return out


def resolve_project(ref: str | None) -> str:
    projects = model.list_all()
    if ref:
        for p in projects:
            if p["id"] == ref or p["name"] == ref:
                return p["id"]
        low = str(ref).lower()
        for p in projects:
            if low in p["name"].lower():
                return p["id"]
        raise UserError(f"No project matches {ref!r}. Use list_projects to see what exists.")
    if ACTIVE["pid"] and model.load(ACTIVE["pid"]):
        return ACTIVE["pid"]
    if not projects:
        raise UserError("There are no projects yet. Create one with create_project.")
    return projects[0]["id"]


def call(name: str, args: dict) -> dict:
    args = dict(args or {})
    if name == "list_projects":
        return {"projects": [{"id": p["id"], "name": p["name"], "duration": round(p["duration"], 1),
                              "clips": p["clips"], "open_in_studio": p["id"] == ACTIVE["pid"]}
                             for p in model.list_all()]}
    if name == "create_project":
        config.ensure_dirs()
        p = model.new_project(str(args.get("name") or "פרויקט חדש"))
        ACTIVE["pid"] = p["id"]
        return {"id": p["id"], "name": p["name"]}
    if name == "wait_for_job":
        job = jobs.get(str(args.get("job", "")))
        if not job:
            raise UserError("Job not found.")
        deadline = time.time() + min(600.0, max(1.0, float(args.get("timeout") or 60)))
        while job.status in ("queued", "running") and time.time() < deadline:
            time.sleep(0.4)
        return job.public()
    if name not in ops.OPS:
        raise UserError(f"Unknown tool: {name}")
    pid = resolve_project(args.pop("project", None))
    return {"project": pid, **ops_jobs.execute(pid, name, args, local=True)}


async def _list_tools(_ctx, _params) -> types.ListToolsResult:
    return types.ListToolsResult(tools=tools())


async def _call_tool(_ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
    try:
        result = await anyio.to_thread.run_sync(call, params.name, dict(params.arguments or {}))
        text = json.dumps(result, ensure_ascii=False, default=str)
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=False)
    except UserError as e:
        return types.CallToolResult(content=[types.TextContent(type="text", text=str(e))], is_error=True)
    except Exception as e:  # noqa: BLE001 - reported to the agent
        return types.CallToolResult(content=[types.TextContent(type="text", text=f"{type(e).__name__}: {e}")],
                                    is_error=True)


server = Server("studio", version=config.VERSION, title="הסטודיו שלי", instructions=INSTRUCTIONS,
                on_list_tools=_list_tools, on_call_tool=_call_tool)
manager: StreamableHTTPSessionManager | None = None


def start() -> StreamableHTTPSessionManager:
    """A fresh session manager for one run of the web server (it cannot be reused after it stops)."""
    global manager
    # the studio's own gate already checks who is calling, so the library's host check is off
    manager = StreamableHTTPSessionManager(
        app=server, json_response=True, stateless=True,
        security_settings=TransportSecuritySettings(enable_dns_rebinding_protection=False))
    return manager


class Endpoint:
    """ASGI entry point mounted at /mcp."""

    async def __call__(self, scope, receive, send):
        await manager.handle_request(scope, receive, send)
