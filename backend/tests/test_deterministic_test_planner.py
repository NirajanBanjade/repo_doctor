"""Tests for the offline, AST-backed test planner."""

from __future__ import annotations

from app.services.deterministic_test_planner import build_deterministic_scenarios


def test_builds_scenarios_from_branches_raises_and_route(tmp_path):
    source = tmp_path / "users.py"
    source.write_text(
        """\
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/users", status_code=201)
def create_user(email: str):
    if not email:
        raise HTTPException(status_code=422)
    return {"email": email}
""",
        encoding="utf-8",
    )
    node = {
        "node_id": "users.py::create_user",
        "name": "create_user",
        "path": "users.py",
        "line_start": 6,
        "line_end": 10,
    }

    scenarios = build_deterministic_scenarios(str(tmp_path), [node])

    assert len(scenarios) == 4
    assert any("normal path" in scenario["name"] for scenario in scenarios)
    assert any("branch" in scenario["name"] for scenario in scenarios)
    assert any("error path" in scenario["name"] for scenario in scenarios)
    assert any("POST" in scenario["name"] for scenario in scenarios)
    assert all(
        scenario["source_evidence"].startswith("users.py:") for scenario in scenarios
    )


def test_uses_source_contract_for_unsupported_file(tmp_path):
    (tmp_path / "component.ts").write_text("export const value = 1;", encoding="utf-8")
    node = {
        "node_id": "component.ts",
        "name": "component.ts",
        "path": "component.ts",
        "line_start": 1,
    }

    scenarios = build_deterministic_scenarios(str(tmp_path), [node])

    assert len(scenarios) == 1
    assert scenarios[0]["name"] == "Validate source contract for component.ts"


def test_does_not_read_paths_outside_repository(tmp_path):
    node = {
        "node_id": "outside::secret",
        "name": "secret",
        "path": "../outside.py",
        "line_start": 1,
    }

    scenarios = build_deterministic_scenarios(str(tmp_path), [node])

    assert len(scenarios) == 1
    assert "source contract" in scenarios[0]["name"].lower()
