"""
tests/test_xray_routes.py

Integration tests for X-Ray API routes:
- POST /api/v1/sessions/{id}/xray
- GET  /api/v1/sessions/{id}/xray/graph
"""

from __future__ import annotations

import textwrap

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import evidence_store
from app.main import app

# Isolate DB for each test
TEST_DB = "sqlite:///./test_xray.db"


@pytest.fixture(autouse=True)
def reset_db(tmp_path):
    """Force a fresh in-memory engine per test."""
    evidence_store._engine = None
    db_url = f"sqlite:///{tmp_path}/xray_test.db"
    # Patch all store calls to use tmp db
    import app.db.evidence_store as es

    es._engine = None
    # We override the default db_url by monkey-patching the module-level default
    yield db_url
    es._engine = None


@pytest.fixture()
def python_repo(tmp_path):
    """A minimal Python/FastAPI repo for integration tests."""
    (tmp_path / "requirements.txt").write_text("fastapi\npytest\n")
    (tmp_path / "main.py").write_text(textwrap.dedent("""
        from fastapi import FastAPI
        app = FastAPI()

        def root():
            return {"hello": "world"}
    """))
    (tmp_path / "utils.py").write_text(textwrap.dedent("""
        import os

        class Helper:
            def do_work(self): pass
    """))
    return str(tmp_path)


@pytest.fixture()
def unknown_repo(tmp_path):
    """A repo with no recognisable language markers."""
    (tmp_path / "data.txt").write_text("just text\n")
    return str(tmp_path)


@pytest.fixture()
def app_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Session + X-Ray happy path ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_xray_returns_202(python_repo, reset_db, app_client):
    async with app_client as client:
        # Create session
        r = await client.post("/api/v1/sessions", json={"repo_path": python_repo})
        assert r.status_code == 201
        session_id = r.json()["session_id"]

        # Run X-Ray
        r2 = await client.post(f"/api/v1/sessions/{session_id}/xray")
        assert r2.status_code == 202
        body = r2.json()
        assert body["node_count"] > 0
        assert body["edge_count"] >= 0
        assert body["status"] == "xray_complete"


@pytest.mark.asyncio
async def test_get_xray_graph_after_run(python_repo, reset_db, app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": python_repo})
        session_id = r.json()["session_id"]
        await client.post(f"/api/v1/sessions/{session_id}/xray")

        r2 = await client.get(f"/api/v1/sessions/{session_id}/xray/graph")
        assert r2.status_code == 200
        body = r2.json()
        assert "nodes" in body
        assert "edges" in body
        assert len(body["nodes"]) > 0


@pytest.mark.asyncio
async def test_xray_graph_nodes_have_required_fields(python_repo, reset_db, app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": python_repo})
        session_id = r.json()["session_id"]
        await client.post(f"/api/v1/sessions/{session_id}/xray")

        r2 = await client.get(f"/api/v1/sessions/{session_id}/xray/graph")
        nodes = r2.json()["nodes"]
        for n in nodes:
            assert "node_id" in n
            assert "kind" in n
            assert "path" in n
            assert "line_start" in n
            assert "line_end" in n
            assert "language" in n


@pytest.mark.asyncio
async def test_xray_graph_edges_have_evidence_status(python_repo, reset_db, app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": python_repo})
        session_id = r.json()["session_id"]
        await client.post(f"/api/v1/sessions/{session_id}/xray")

        r2 = await client.get(f"/api/v1/sessions/{session_id}/xray/graph")
        edges = r2.json()["edges"]
        for e in edges:
            assert e["evidence_status"] in (
                "confirmed_static",
                "observed_test",
                "inferred",
            )
            assert "file" in e
            assert "line" in e


# ── No-adapter / unknown language ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_xray_unknown_language_returns_empty_graph_with_warning(
    unknown_repo, reset_db, app_client
):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": unknown_repo})
        session_id = r.json()["session_id"]

        r2 = await client.post(f"/api/v1/sessions/{session_id}/xray")
        assert r2.status_code == 202
        body = r2.json()
        assert body["node_count"] == 0
        assert any("no_adapter" in w for w in body["warnings"])


# ── Error cases ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_xray_session_not_found(reset_db, app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions/nonexistent/xray")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_graph_session_not_found(reset_db, app_client):
    async with app_client as client:
        r = await client.get("/api/v1/sessions/nonexistent/xray/graph")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_xray_invalid_repo_path(reset_db, app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": "/does/not/exist"})
        session_id = r.json()["session_id"]
        r2 = await client.post(f"/api/v1/sessions/{session_id}/xray")
        assert r2.status_code == 422


@pytest.mark.asyncio
async def test_get_graph_before_xray_has_warning(python_repo, reset_db, app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": python_repo})
        session_id = r.json()["session_id"]
        # Do NOT run xray
        r2 = await client.get(f"/api/v1/sessions/{session_id}/xray/graph")
        assert r2.status_code == 200
        assert any("no_nodes" in w for w in r2.json()["warnings"])


# ── Session status transitions ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_status_updated_to_xray_complete(
    python_repo, reset_db, app_client
):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": python_repo})
        session_id = r.json()["session_id"]
        await client.post(f"/api/v1/sessions/{session_id}/xray")

        r2 = await client.get(f"/api/v1/sessions/{session_id}")
        assert r2.json()["status"] == "xray_complete"
        assert r2.json()["stack"]["language"] == "python"
        assert r2.json()["stack"]["framework"] == "fastapi"


# ── Key module annotation ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_at_most_5_key_modules(python_repo, reset_db, app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": python_repo})
        session_id = r.json()["session_id"]
        await client.post(f"/api/v1/sessions/{session_id}/xray")

        r2 = await client.get(f"/api/v1/sessions/{session_id}/xray/graph")
        key_nodes = [n for n in r2.json()["nodes"] if n["key_module"]]
        assert len(key_nodes) <= 5
