"""
app/api/routes/tests.py

POST /api/v1/sessions/{session_id}/tests/plan          — create or retrieve TestPlanProposal
POST /api/v1/sessions/{session_id}/tests/plan/{plan_id}/approve — approve or reject plan
POST /api/v1/sessions/{session_id}/tests/plan/{plan_id}/run    — execute approved plan
GET  /api/v1/sessions/{session_id}/tests/plan/{plan_id}/result — get latest TestRunResult
"""

from __future__ import annotations

import logging
import os
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.bob.integration import run_test_agent
from app.db import evidence_store
from app.sandbox.test_executor import build_component_statuses, run_tests
from app.services import session as session_svc
from app.services.test_generator import ApprovalRequiredError, generate_test_files
from app.services.test_mapper import map_tests_to_nodes

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Working-copy root ──────────────────────────────────────────────────────────
_WORKING_COPY_ROOT = os.environ.get("REPODOC_WORKING_COPY", "./working_copy")


# ── Request/response schemas ───────────────────────────────────────────────────


class PlanRequest(BaseModel):
    impact_run_id: str
    selected_node_ids: list[str]
    change_description: str | None = None
    diff_content: str | None = None


class ApprovalRequest(BaseModel):
    plan_id: str
    approved: bool


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.post("/{session_id}/tests/plan", status_code=202)
async def create_test_plan(session_id: str, body: PlanRequest) -> dict:
    """
    Create (or retrieve an existing) TestPlanProposal for the given impact run.
    Invokes Test Agent via Bob; degrades to empty scenario list if Bob unavailable.
    """
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    impact_run = evidence_store.get_impact_run(body.impact_run_id)
    if impact_run is None:
        raise HTTPException(status_code=404, detail="Impact run not found")

    # Return existing plan if already created for this impact run
    existing = evidence_store.get_test_plan_by_impact_run(body.impact_run_id)
    if existing is not None:
        return _plan_response(existing)

    # Fetch node details for selected nodes
    all_nodes = evidence_store.get_nodes(session_id)
    node_map = {n["node_id"]: n for n in all_nodes}
    selected_nodes = [
        {
            "node_id": nid,
            "name": node_map[nid]["name"] if nid in node_map else nid,
            "path": node_map[nid]["path"] if nid in node_map else "",
            "line_start": node_map[nid]["line_start"] if nid in node_map else 0,
            "line_end": node_map[nid]["line_end"] if nid in node_map else 0,
        }
        for nid in body.selected_node_ids
    ]

    # Test Mapper: find existing tests for each node
    repo_path = s["repo_path"]
    mappings = map_tests_to_nodes(repo_path, selected_nodes)
    mapping_dicts = [
        {
            "node_id": m.node_id,
            "test_files": m.test_files,
            "coverage_status": m.coverage_status,
        }
        for m in mappings
    ]

    # Test Agent (graceful degradation)
    proposal = await run_test_agent(
        session_id=session_id,
        selected_nodes=selected_nodes,
        existing_test_mappings=mapping_dicts,
        change_description=body.change_description,
        diff_content=body.diff_content,
    )

    scenarios = [s.model_dump() for s in proposal.scenarios] if proposal else []

    plan_id = str(uuid.uuid4())
    evidence_store.save_test_plan(
        plan_id=plan_id,
        session_id=session_id,
        impact_run_id=body.impact_run_id,
        scenarios=scenarios,
    )

    plan = evidence_store.get_test_plan(plan_id)
    return _plan_response(plan, existing_mappings=mapping_dicts)


@router.post("/{session_id}/tests/plan/{plan_id}/approve", status_code=200)
async def approve_test_plan(
    session_id: str, plan_id: str, body: ApprovalRequest
) -> dict:
    """
    Approve or reject a pending test plan.
    Requires plan_id in body to match URL plan_id.
    """
    if body.plan_id != plan_id:
        raise HTTPException(
            status_code=422, detail="plan_id in body does not match URL"
        )

    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    plan = evidence_store.get_test_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Test plan not found")

    if plan["session_id"] != session_id:
        raise HTTPException(status_code=403, detail="Plan does not belong to session")

    new_status = "approved" if body.approved else "rejected"
    evidence_store.update_test_plan_status(plan_id, new_status)

    return {"plan_id": plan_id, "status": new_status}


@router.post("/{session_id}/tests/plan/{plan_id}/run", status_code=202)
async def run_test_plan(session_id: str, plan_id: str) -> dict:
    """
    Execute an approved test plan in the Docker sandbox.
    Generates test files into working_copy/, then runs pytest.
    Returns TestRunResult.
    """
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    plan = evidence_store.get_test_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Test plan not found")

    if plan["session_id"] != session_id:
        raise HTTPException(status_code=403, detail="Plan does not belong to session")

    if plan["status"] != "approved":
        raise HTTPException(
            status_code=422,
            detail=f"Plan status is '{plan['status']}'; must be 'approved' before running.",
        )

    repo_path = s["repo_path"]
    working_copy_root = os.path.abspath(_WORKING_COPY_ROOT)

    # Generate test files
    try:
        generated_files = generate_test_files(plan, working_copy_root)
    except ApprovalRequiredError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Gather existing test files from mapping context
    # (we re-run the mapper to get current file list)
    node_map_all = {n["node_id"]: n for n in evidence_store.get_nodes(session_id)}
    scenario_node_ids = [sc.get("component_id") for sc in (plan.get("scenarios") or [])]
    selected_nodes_for_mapper = [
        node_map_all[nid] for nid in scenario_node_ids if nid in node_map_all
    ]
    existing_test_files: list[str] = []
    if selected_nodes_for_mapper:
        mappings = map_tests_to_nodes(repo_path, selected_nodes_for_mapper)
        for m in mappings:
            for tf in m.test_files:
                full = tf if os.path.isabs(tf) else os.path.join(repo_path, tf)
                if full not in existing_test_files:
                    existing_test_files.append(full)

    generated_dir = os.path.join(working_copy_root, "tests", "generated")
    result = await run_tests(
        repo_path=repo_path,
        working_copy_root=working_copy_root,
        existing_test_files=existing_test_files,
        generated_dir=generated_dir,
    )

    component_statuses = build_component_statuses(
        scenarios=plan.get("scenarios") or [],
        per_test=result["per_test"],
        generated_files=generated_files,
        infrastructure_error=result["infrastructure_error"],
    )

    result_id = str(uuid.uuid4())
    evidence_store.save_test_result(
        result_id=result_id,
        plan_id=plan_id,
        session_id=session_id,
        stdout=result["stdout"],
        stderr=result["stderr"],
        exit_code=result["exit_code"],
        infrastructure_error=result["infrastructure_error"],
        per_test=result["per_test"],
        component_statuses=component_statuses,
    )

    no_test_nodes = [
        cs["component_id"]
        for cs in component_statuses
        if cs["status"] == "no_suitable_test"
    ]

    return {
        "result_id": result_id,
        "plan_id": plan_id,
        "session_id": session_id,
        "infrastructure_error": result["infrastructure_error"],
        "per_test": result["per_test"],
        "component_statuses": component_statuses,
        "generated_files": generated_files,
        "warnings": _build_run_warnings(
            result, component_statuses, no_test_nodes, plan
        ),
    }


@router.get("/{session_id}/tests/plan/{plan_id}/result")
async def get_test_result(session_id: str, plan_id: str) -> dict:
    """Return the latest test run result for this plan."""
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    plan = evidence_store.get_test_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Test plan not found")

    result = evidence_store.get_test_result_by_plan(plan_id)
    if result is None:
        return {
            "session_id": session_id,
            "plan_id": plan_id,
            "result": None,
            "warnings": ["no_test_result: tests have not been run yet"],
        }

    return {
        "session_id": session_id,
        "plan_id": plan_id,
        "result_id": result["result_id"],
        "infrastructure_error": result["infrastructure_error"],
        "per_test": result["per_test"],
        "component_statuses": result["component_statuses"],
    }


# ── Helpers ────────────────────────────────────────────────────────────────────


def _plan_response(plan: dict, existing_mappings: list[dict] | None = None) -> dict:
    return {
        "plan_id": plan["plan_id"],
        "session_id": plan["session_id"],
        "impact_run_id": plan["impact_run_id"],
        "scenarios": plan["scenarios"],
        "status": plan["status"],
        "existing_test_mappings": existing_mappings or [],
    }


def _build_run_warnings(
    result: dict,
    component_statuses: list[dict],
    no_test_nodes: list[str],
    plan: dict,
) -> list[str]:
    warnings: list[str] = [
        (
            "NOTICE: Passing generated tests are NOT proof that every affected component "
            "is safe. The report lists all skipped nodes, inferred edges, and components "
            "with no test."
        )
    ]
    if no_test_nodes:
        warnings.append(
            f"no_suitable_test: {len(no_test_nodes)} component(s) have no test — "
            + ", ".join(no_test_nodes)
        )
    if result["infrastructure_error"]:
        warnings.append(
            "infrastructure_error: sandbox did not complete successfully — "
            "some tests may be unexecuted."
        )
    unexecuted = [
        cs["component_id"] for cs in component_statuses if cs["status"] == "unexecuted"
    ]
    if unexecuted:
        warnings.append(
            f"unexecuted: {len(unexecuted)} component(s) had generated tests that "
            "were not executed due to an infrastructure error — "
            + ", ".join(unexecuted)
        )
    return warnings
