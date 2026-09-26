"""
tests/test_environment_routes.py

Integration tests for Environment Doctor API routes:
  POST /api/v1/sessions/{id}/environment/run
  POST /api/v1/sessions/{id}/environment/fix
  GET  /api/v1/sessions/{id}/environment/checks

Docker is mocked so tests run without a Docker daemon.
"""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import evidence_store
from app.main import app

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_db(tmp_path):
    evidence_store._engine = None
    yield
    evidence_store._engine = None


@pytest.fixture()
def app_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture()
def repo_with_readme(tmp_path):
    """Minimal repo with a README that has two setup commands."""
    readme = textwrap.dedent("""
        # Sample App

        ## Installation

        ```bash
        pip install -r requirements.txt
        python -m pytest
        ```
    """)
    (tmp_path / "README.md").write_text(readme)
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    return str(tmp_path)


@pytest.fixture()
def repo_without_readme(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n")
    return str(tmp_path)


def _make_mock_results(commands: list[str], status: str = "verified") -> list[dict]:
    now = datetime.now(timezone.utc)
    import uuid

    return [
        {
            "step_id": str(uuid.uuid4()),
            "command": cmd,
            "status": status,
            "exit_code": 0 if status == "verified" else 1,
            "stdout": "ok",
            "stderr": "",
            "started_at": now,
            "finished_at": now,
        }
        for cmd in commands
    ]


# ── POST /environment/run ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_returns_202_with_steps(repo_with_readme, app_client):
    mock_results = _make_mock_results(
        ["pip install -r requirements.txt", "python -m pytest"]
    )
    with patch(
        "app.api.routes.environment.run_setup_plan",
        new=AsyncMock(return_value=mock_results),
    ):
        async with app_client as client:
            r = await client.post(
                "/api/v1/sessions", json={"repo_path": repo_with_readme}
            )
            session_id = r.json()["session_id"]

            r2 = await client.post(f"/api/v1/sessions/{session_id}/environment/run")

    assert r2.status_code == 202
    body = r2.json()
    assert body["status"] == "verified"
    assert len(body["steps"]) == 2
    assert body["run_number"] == 1


@pytest.mark.asyncio
async def test_run_session_not_found(app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions/nonexistent/environment/run")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_run_invalid_repo_path(app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": "/does/not/exist"})
        session_id = r.json()["session_id"]
        r2 = await client.post(f"/api/v1/sessions/{session_id}/environment/run")
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_run_no_readme_returns_no_steps(repo_without_readme, app_client):
    async with app_client as client:
        r = await client.post(
            "/api/v1/sessions", json={"repo_path": repo_without_readme}
        )
        session_id = r.json()["session_id"]
        r2 = await client.post(f"/api/v1/sessions/{session_id}/environment/run")

    assert r2.status_code == 202
    body = r2.json()
    assert body["status"] == "no_steps"
    assert body["steps"] == []
    assert any("no_steps" in w for w in body["warnings"])


@pytest.mark.asyncio
async def test_run_persists_steps_to_db(repo_with_readme, app_client):
    mock_results = _make_mock_results(["pip install -r requirements.txt"])
    with patch(
        "app.api.routes.environment.run_setup_plan",
        new=AsyncMock(return_value=mock_results),
    ):
        async with app_client as client:
            r = await client.post(
                "/api/v1/sessions", json={"repo_path": repo_with_readme}
            )
            session_id = r.json()["session_id"]
            await client.post(f"/api/v1/sessions/{session_id}/environment/run")

            r2 = await client.get(f"/api/v1/sessions/{session_id}/environment/checks")

    assert r2.status_code == 200
    steps = r2.json()["steps"]
    assert len(steps) == 1
    assert steps[0]["command"] == "pip install -r requirements.txt"
    assert steps[0]["status"] == "verified"


@pytest.mark.asyncio
async def test_run_step_status_values_are_valid(repo_with_readme, app_client):
    mock_results = _make_mock_results(
        ["pip install -r requirements.txt", "python -m pytest"]
    )
    with patch(
        "app.api.routes.environment.run_setup_plan",
        new=AsyncMock(return_value=mock_results),
    ):
        async with app_client as client:
            r = await client.post(
                "/api/v1/sessions", json={"repo_path": repo_with_readme}
            )
            session_id = r.json()["session_id"]
            r2 = await client.post(f"/api/v1/sessions/{session_id}/environment/run")

    valid_statuses = {"verified", "failed", "blocked", "infrastructure_error"}
    for step in r2.json()["steps"]:
        assert step["status"] in valid_statuses


@pytest.mark.asyncio
async def test_failed_step_marks_overall_status_failed(repo_with_readme, app_client):
    """A single failed step means the overall run status is 'failed'."""
    import uuid
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    mock_results = [
        {
            "step_id": str(uuid.uuid4()),
            "command": "pip install -r requirements.txt",
            "status": "failed",
            "exit_code": 1,
            "stdout": "",
            "stderr": "ERROR: could not find package",
            "started_at": now,
            "finished_at": now,
        },
        {
            "step_id": str(uuid.uuid4()),
            "command": "python -m pytest",
            "status": "blocked",
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "started_at": now,
            "finished_at": now,
        },
    ]
    with patch(
        "app.api.routes.environment.run_setup_plan",
        new=AsyncMock(return_value=mock_results),
    ):
        async with app_client as client:
            r = await client.post(
                "/api/v1/sessions", json={"repo_path": repo_with_readme}
            )
            session_id = r.json()["session_id"]
            r2 = await client.post(f"/api/v1/sessions/{session_id}/environment/run")

    body = r2.json()
    assert body["status"] == "failed"
    statuses = [s["status"] for s in body["steps"]]
    assert "failed" in statuses
    assert "blocked" in statuses


# ── POST /environment/fix ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fix_without_approval_returns_400(repo_with_readme, app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": repo_with_readme})
        session_id = r.json()["session_id"]
        r2 = await client.post(
            f"/api/v1/sessions/{session_id}/environment/fix",
            json={
                "step_id": "some-step-id",
                "fix_description": "Install libpq-dev",
                "approval": False,
            },
        )
    assert r2.status_code == 400
    assert "approval" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_fix_with_approval_reruns_setup(repo_with_readme, app_client):
    mock_results = _make_mock_results(["pip install -r requirements.txt"])
    with patch(
        "app.api.routes.environment.run_setup_plan",
        new=AsyncMock(return_value=mock_results),
    ):
        async with app_client as client:
            r = await client.post(
                "/api/v1/sessions", json={"repo_path": repo_with_readme}
            )
            session_id = r.json()["session_id"]
            r2 = await client.post(
                f"/api/v1/sessions/{session_id}/environment/fix",
                json={
                    "step_id": "some-step-id",
                    "fix_description": "Install libpq-dev",
                    "approval": True,
                },
            )

    assert r2.status_code == 202
    body = r2.json()
    assert body["status"] == "verified"
    assert body["fix_applied"] is False  # no patch_content supplied


@pytest.mark.asyncio
async def test_fix_increments_run_number(repo_with_readme, app_client):
    mock_results = _make_mock_results(["pip install -r requirements.txt"])
    with patch(
        "app.api.routes.environment.run_setup_plan",
        new=AsyncMock(return_value=mock_results),
    ):
        async with app_client as client:
            r = await client.post(
                "/api/v1/sessions", json={"repo_path": repo_with_readme}
            )
            session_id = r.json()["session_id"]

            # First run
            r1 = await client.post(f"/api/v1/sessions/{session_id}/environment/run")
            # Fix/re-run
            r2 = await client.post(
                f"/api/v1/sessions/{session_id}/environment/fix",
                json={
                    "step_id": "s1",
                    "fix_description": "fix",
                    "approval": True,
                },
            )

    assert r1.json()["run_number"] == 1
    assert r2.json()["run_number"] == 2


@pytest.mark.asyncio
async def test_fix_session_not_found(app_client):
    async with app_client as client:
        r = await client.post(
            "/api/v1/sessions/nonexistent/environment/fix",
            json={
                "step_id": "s1",
                "fix_description": "fix",
                "approval": True,
            },
        )
    assert r.status_code == 404


# ── GET /environment/checks ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_checks_session_not_found(app_client):
    async with app_client as client:
        r = await client.get("/api/v1/sessions/nonexistent/environment/checks")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_checks_returns_empty_before_run(repo_with_readme, app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": repo_with_readme})
        session_id = r.json()["session_id"]
        r2 = await client.get(f"/api/v1/sessions/{session_id}/environment/checks")

    assert r2.status_code == 200
    assert r2.json()["steps"] == []


@pytest.mark.asyncio
async def test_get_checks_filters_by_run_number(repo_with_readme, app_client):
    mock_results = _make_mock_results(["pip install -r requirements.txt"])
    with patch(
        "app.api.routes.environment.run_setup_plan",
        new=AsyncMock(return_value=mock_results),
    ):
        async with app_client as client:
            r = await client.post(
                "/api/v1/sessions", json={"repo_path": repo_with_readme}
            )
            session_id = r.json()["session_id"]
            # Two runs
            await client.post(f"/api/v1/sessions/{session_id}/environment/run")
            await client.post(
                f"/api/v1/sessions/{session_id}/environment/fix",
                json={"step_id": "s1", "fix_description": "fix", "approval": True},
            )

            r2 = await client.get(
                f"/api/v1/sessions/{session_id}/environment/checks?run_number=1"
            )
            r3 = await client.get(
                f"/api/v1/sessions/{session_id}/environment/checks?run_number=2"
            )

    assert all(s["run_number"] == 1 for s in r2.json()["steps"])
    assert all(s["run_number"] == 2 for s in r3.json()["steps"])
