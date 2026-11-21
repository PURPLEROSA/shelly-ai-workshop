import json

import pytest
from starlette.testclient import TestClient

from app import mcp_server, model, ops, server
from app.jobs import UserError

from helpers import project_with_clip, spoken

HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def rpc(client, method, params=None, rid=1, headers=None):
    body = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
    return client.post("/mcp", content=json.dumps(body), headers={**HEADERS, **(headers or {})})


@pytest.fixture()
def local():
    with TestClient(server.app, base_url="http://localhost:8765", client=("127.0.0.1", 50000)) as c:
        yield c


def test_handshake_and_tool_list(local):
    init = rpc(local, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "test", "version": "1"}}).json()["result"]
    assert "tools" in init["capabilities"] and "video editing studio" in init["instructions"]
    tools = rpc(local, "tools/list", rid=2).json()["result"]["tools"]
    names = {t["name"] for t in tools}
    assert len(tools) == len(ops.OPS) + len(mcp_server.EXTRA) >= 58
    assert {"get_project", "delete_words", "remove_silences", "set_captions", "export", "wait_for_job",
            "list_projects", "add_narration", "search_stock", "quick_zoom"} <= names
    for t in tools:
        assert t["inputSchema"]["type"] == "object" and t["description"]


def test_tool_calls_edit_the_open_project(local):
    pid, mid, iid = project_with_clip(20.0, spoken(30))
    mcp_server.ACTIVE["pid"] = pid
    r = rpc(local, "tools/call", {"name": "remove_silences", "arguments": {"level": "normal"}}, 3).json()["result"]
    assert r["isError"] is False and json.loads(r["content"][0]["text"])["pause_tightening"] == 0.35
    assert model.load(pid)["tighten"] == 0.35
    r = rpc(local, "tools/call", {"name": "delete_words", "arguments": {"project": pid, "media": mid, "from": 0, "to": 2}}, 4).json()["result"]
    assert json.loads(r["content"][0]["text"])["changed"] == 3
    r = rpc(local, "tools/call", {"name": "split_item", "arguments": {"at": 999}}, 5).json()["result"]
    assert r["isError"] is True and r["content"][0]["text"]
    r = rpc(local, "tools/call", {"name": "undo", "arguments": {}}, 6).json()["result"]
    assert r["isError"] is False and not model.load(pid)["media"][mid]["words"][0].get("d")
    projects = json.loads(rpc(local, "tools/call", {"name": "list_projects", "arguments": {}}, 7).json()["result"]["content"][0]["text"])
    assert any(p["id"] == pid and p["open_in_studio"] for p in projects["projects"])


def test_project_can_be_named_or_defaulted():
    pid, _, _ = project_with_clip(5.0)
    name = model.load(pid)["name"]
    mcp_server.ACTIVE["pid"] = None
    assert mcp_server.resolve_project(pid) == pid
    assert mcp_server.resolve_project(name) in {p["id"] for p in model.list_all() if p["name"] == name}
    with pytest.raises(UserError):
        mcp_server.resolve_project("no such project anywhere")
    assert mcp_server.resolve_project(None) == model.list_all()[0]["id"]


def test_other_devices_need_the_token():
    with TestClient(server.app, base_url="http://192.168.1.20:8765", client=("192.168.1.77", 50000)) as c:
        assert rpc(c, "tools/list").status_code == 403
        assert c.get("/api/projects").status_code == 403
        token = __import__("app.config", fromlist=["x"]).load_settings()["token"]
        ok = rpc(c, "tools/list", headers={"Authorization": f"Bearer {token}"})
        assert ok.status_code == 200 and ok.json()["result"]["tools"]
        # local-only operations stay local even with the token
        pid, _, _ = project_with_clip(5.0)
        r = c.post(f"/api/projects/{pid}/ops", json={"op": "import_media", "args": {"source": "/etc/hosts"}},
                   headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 400
        assert c.put("/api/settings", json={"mobile_access": False}, headers={"Authorization": f"Bearer {token}"}).status_code == 403


def test_rest_ops_endpoint_returns_fresh_state(local):
    pid, mid, iid = project_with_clip(20.0, spoken(10))
    r = local.post(f"/api/projects/{pid}/ops", json={"op": "split_item", "args": {"at": 4}}).json()
    assert len(r["derived"]["order"]) == 2 and "words" not in r["doc"]["media"][mid]
    r = local.post(f"/api/projects/{pid}/ops", json={"op": "delete_words", "args": {"media": mid, "from": 1, "to": 1}}).json()
    assert r["doc"]["media"][mid]["words"][1]["d"] is True
    assert local.post(f"/api/projects/{pid}/ops", json={"op": "nope"}).status_code == 400
    cat = local.get("/api/ops").json()["ops"]
    assert len(cat) == len(ops.OPS)
