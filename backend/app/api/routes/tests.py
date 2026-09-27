"""
app/api/routes/tests.py

POST /api/v1/sessions/{session_id}/tests/plan          — create or retrieve TestPlanProposal
POST /api/v1/sessions/{session_id}/tests/plan/{plan_id}/approve — approve or reject plan
POST /api/v1/sessions/{session_id}/tests/plan/{plan_id}/run    — execute approved plan
GET  /api/v1/sessions/{session_id}/tests/plan/{plan_id}/result — get latest TestRunResult
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.bob.integration import run_test_agent
from app.db import evidence_store
from app.sandbox.test_executor import build_component_statuses, run_tests
from app.services import session as session_svc
from app.services.deterministic_test_planner import build_deterministic_scenarios
from app.services.feature_wiki import parse_feature_wiki
from app.services.test_generator import generate_test_files, generated_test_filename
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


class RefineRequest(BaseModel):
    feedback: str


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/{session_id}/tests/plan")
async def get_latest_test_plan(session_id: str) -> dict:
    """Return the plan for the session's latest impact run."""
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    impact_run = evidence_store.get_latest_impact_run(session_id)
    if impact_run is None:
        raise HTTPException(status_code=404, detail="No impact run found")
    plan = evidence_store.get_test_plan_by_impact_run(impact_run["run_id"])
    if plan is None:
        raise HTTPException(status_code=404, detail="No test plan found")
    _, suggestions = _wiki_test_scope(s, impact_run)
    mappings = _mappings_for_plan(s, plan)
    return _plan_response(
        plan,
        existing_mappings=mappings,
        external_feature_suggestions=suggestions,
    )


@router.get("/{session_id}/tests/results")
async def get_latest_test_results(session_id: str) -> dict:
    """Return the latest test result using the frontend's session-level route."""
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    impact_run = evidence_store.get_latest_impact_run(session_id)
    plan = (
        evidence_store.get_test_plan_by_impact_run(impact_run["run_id"])
        if impact_run
        else None
    )
    result = evidence_store.get_test_result_by_plan(plan["plan_id"]) if plan else None
    if result is None:
        raise HTTPException(status_code=404, detail="No test result found")
    return {
        "run_id": result["result_id"],
        "plan_id": result["plan_id"],
        "session_id": session_id,
        "component_statuses": result["component_statuses"],
        "test_results": _test_case_results(
            result["per_test"], plan.get("scenarios") or []
        ),
        "sandbox_exit_code": result["exit_code"],
        "infrastructure_error": (
            "Sandbox execution failed" if result["infrastructure_error"] else None
        ),
    }


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
    if impact_run["session_id"] != session_id:
        raise HTTPException(
            status_code=403, detail="Impact run does not belong to session"
        )

    impact_node_ids = {
        row["node_id"] for row in evidence_store.get_impact_nodes(body.impact_run_id)
    }
    if not body.selected_node_ids:
        raise HTTPException(
            status_code=422, detail="Select at least one impacted component"
        )
    invalid_node_ids = [
        node_id for node_id in body.selected_node_ids if node_id not in impact_node_ids
    ]
    if invalid_node_ids:
        raise HTTPException(
            status_code=422,
            detail=f"Selected components are not in this impact run: {invalid_node_ids}",
        )

    _, external_suggestions = _wiki_test_scope(s, impact_run)
    requested_node_ids = list(dict.fromkeys(body.selected_node_ids))

    # Return existing plan if already created for this impact run
    existing = evidence_store.get_test_plan_by_impact_run(body.impact_run_id)
    if existing is not None:
        return _plan_response(
            existing,
            existing_mappings=_mappings_for_plan(s, existing),
            external_feature_suggestions=external_suggestions,
        )

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
        for nid in requested_node_ids
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

    scenarios = (
        [scenario.model_dump() for scenario in proposal.scenarios]
        if proposal
        else build_deterministic_scenarios(repo_path, selected_nodes)
    )
    analysis_notes = (
        proposal.analysis_notes
        if proposal
        else [
            (
                "Bob analysis was unavailable. RepoDoc derived scenarios from explicit "
                "Python branches, exceptions, routes, and source contracts."
            )
        ]
    )
    overall_rationale = (
        proposal.overall_rationale
        if proposal
        else (
            "The selected components have an offline, evidence-backed plan derived from "
            "their source structure. These scenarios do not infer unstated business rules."
        )
    )

    plan_id = str(uuid.uuid4())
    evidence_store.save_test_plan(
        plan_id=plan_id,
        session_id=session_id,
        impact_run_id=body.impact_run_id,
        scenarios=scenarios,
        analysis_notes=analysis_notes,
        overall_rationale=overall_rationale,
    )

    plan = evidence_store.get_test_plan(plan_id)
    return _plan_response(
        plan,
        existing_mappings=mapping_dicts,
        external_feature_suggestions=external_suggestions,
    )


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

    if plan["status"] != "proposed":
        raise HTTPException(
            status_code=422,
            detail=f"Plan status is '{plan['status']}'; only proposed plans can be reviewed.",
        )

    if not body.approved:
        evidence_store.update_test_plan_status(plan_id, "rejected")
        rejected = evidence_store.get_test_plan(plan_id)
        return _plan_response(rejected, existing_mappings=_mappings_for_plan(s, plan))

    evidence_store.update_test_plan_status(plan_id, "approved")
    approved = evidence_store.get_test_plan(plan_id)
    working_copy_root = os.path.abspath(_WORKING_COPY_ROOT)
    generated_files = await asyncio.to_thread(
        generate_test_files, approved, working_copy_root
    )
    generated_paths = set(generated_files)
    scenarios = []
    for index, scenario in enumerate(approved.get("scenarios") or [], start=1):
        updated = dict(scenario)
        expected_path = os.path.join(
            working_copy_root,
            "tests",
            "generated",
            generated_test_filename(scenario, index),
        )
        generated_path = expected_path if expected_path in generated_paths else ""
        updated["generation_status"] = "generated" if generated_path else "failed"
        updated["generated_test_file"] = generated_path or ""
        scenarios.append(updated)
    evidence_store.update_test_plan_scenarios(
        plan_id=plan_id,
        scenarios=scenarios,
        analysis_notes=approved.get("analysis_notes") or [],
        overall_rationale=approved.get("overall_rationale") or "",
    )
    updated_plan = evidence_store.get_test_plan(plan_id)
    return _plan_response(
        updated_plan,
        existing_mappings=_mappings_for_plan(s, updated_plan),
    )


@router.post("/{session_id}/tests/plan/{plan_id}/refine", status_code=200)
async def refine_test_plan(session_id: str, plan_id: str, body: RefineRequest) -> dict:
    """
    Re-run the Test Agent with user feedback to update scenarios in-place.
    Only allowed while plan is in 'proposed' status (not yet approved/rejected).
    """
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    plan = evidence_store.get_test_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Test plan not found")

    if plan["session_id"] != session_id:
        raise HTTPException(status_code=403, detail="Plan does not belong to session")

    if plan["status"] != "proposed":
        raise HTTPException(
            status_code=422,
            detail=f"Plan status is '{plan['status']}'; can only refine a 'proposed' plan.",
        )

    # Re-fetch node details for the scenarios already in the plan
    all_nodes = evidence_store.get_nodes(session_id)
    node_map = {n["node_id"]: n for n in all_nodes}
    scenario_node_ids = list(
        dict.fromkeys(sc.get("component_id") for sc in (plan.get("scenarios") or []))
    )
    selected_nodes = [
        {
            "node_id": nid,
            "name": node_map[nid]["name"] if nid in node_map else nid,
            "path": node_map[nid]["path"] if nid in node_map else "",
            "line_start": node_map[nid]["line_start"] if nid in node_map else 0,
            "line_end": node_map[nid]["line_end"] if nid in node_map else 0,
        }
        for nid in scenario_node_ids
    ]

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

    proposal = await run_test_agent(
        session_id=session_id,
        selected_nodes=selected_nodes,
        existing_test_mappings=mapping_dicts,
        change_description=body.feedback,
        diff_content=None,
    )

    new_scenarios = (
        [s.model_dump() for s in proposal.scenarios]
        if proposal
        else plan.get("scenarios") or []
    )
    new_notes = (
        proposal.analysis_notes if proposal else plan.get("analysis_notes") or []
    )
    new_rationale = (
        proposal.overall_rationale if proposal else plan.get("overall_rationale") or ""
    )

    evidence_store.update_test_plan_scenarios(
        plan_id=plan_id,
        scenarios=new_scenarios,
        analysis_notes=new_notes,
        overall_rationale=new_rationale,
    )

    updated = evidence_store.get_test_plan(plan_id)
    _, external_suggestions = _wiki_test_scope(
        s, evidence_store.get_impact_run(plan["impact_run_id"]) or {}
    )
    return _plan_response(
        updated,
        existing_mappings=mapping_dicts,
        external_feature_suggestions=external_suggestions,
    )


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

    generated_files = [
        scenario.get("generated_test_file", "")
        for scenario in (plan.get("scenarios") or [])
        if scenario.get("generation_status") == "generated"
        and scenario.get("generated_test_file")
    ]
    missing_generated_files = [
        path for path in generated_files if not os.path.isfile(path)
    ]
    if missing_generated_files or (plan.get("scenarios") and not generated_files):
        raise HTTPException(
            status_code=422,
            detail="Approved test files are missing. Recreate the test plan and approve it again.",
        )

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


def _plan_response(
    plan: dict,
    existing_mappings: list[dict] | None = None,
    external_feature_suggestions: list[dict] | None = None,
) -> dict:
    return {
        "plan_id": plan["plan_id"],
        "session_id": plan["session_id"],
        "impact_run_id": plan["impact_run_id"],
        "scenarios": plan["scenarios"],
        "status": plan["status"],
        "analysis_notes": plan.get("analysis_notes") or [],
        "overall_rationale": plan.get("overall_rationale") or "",
        "existing_test_mappings": existing_mappings or [],
        "coverage_gaps": [
            mapping["node_id"]
            for mapping in (existing_mappings or [])
            if mapping["coverage_status"] == "none"
        ],
        "selected_node_ids": list(
            dict.fromkeys(
                scenario.get("component_id")
                for scenario in (plan.get("scenarios") or [])
                if scenario.get("component_id")
            )
        ),
        "generated_files": [
            scenario.get("generated_test_file")
            for scenario in (plan.get("scenarios") or [])
            if scenario.get("generated_test_file")
        ],
        "external_feature_suggestions": external_feature_suggestions or [],
    }


def _mappings_for_plan(session: dict, plan: dict) -> list[dict]:
    node_map = {
        n["node_id"]: n for n in evidence_store.get_nodes(session["session_id"])
    }
    selected_nodes = [
        node_map[scenario["component_id"]]
        for scenario in (plan.get("scenarios") or [])
        if scenario.get("component_id") in node_map
    ]
    return [
        {
            "node_id": mapping.node_id,
            "test_files": mapping.test_files,
            "coverage_status": mapping.coverage_status,
        }
        for mapping in map_tests_to_nodes(session["repo_path"], selected_nodes)
    ]


def _wiki_test_scope(session: dict, impact_run: dict) -> tuple[list[str], list[dict]]:
    architecture_path = (session.get("stack") or {}).get("architecture_path")
    if not architecture_path:
        return [], []
    architecture = parse_feature_wiki(session["repo_path"], architecture_path)
    origins = set(impact_run.get("origin_ids") or [])
    primary = next(
        (
            feature
            for feature in architecture.features
            if origins and origins.issubset({f"file:{path}" for path in feature.files})
        ),
        None,
    )
    if primary is None:
        return [], []
    by_id = {feature.feature_id: feature for feature in architecture.features}
    suggestions = [
        {
            "feature_id": feature_id,
            "name": by_id[feature_id].name,
            "reason": "Connected to the primary feature; tests are not included yet",
        }
        for feature_id in primary.connected_feature_ids
        if feature_id in by_id
    ]
    return [f"file:{path}" for path in primary.files], suggestions


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


def _test_case_results(per_test: list[dict], scenarios: list[dict]) -> list[dict]:
    scenario_components = [
        (
            str(scenario.get("proposed_test_function") or ""),
            str(scenario.get("component_id") or ""),
        )
        for scenario in scenarios
    ]
    formatted: list[dict] = []
    for index, test in enumerate(per_test, start=1):
        nodeid = str(test.get("nodeid") or "")
        parts = nodeid.split("::")
        test_file = parts[0] if parts else nodeid
        test_function = parts[-1] if len(parts) > 1 else nodeid
        outcome = str(test.get("outcome") or "error")
        status = (
            outcome if outcome in {"passed", "failed", "error", "skipped"} else "error"
        )
        linked_node_ids = [
            component_id
            for function_name, component_id in scenario_components
            if function_name and function_name in nodeid and component_id
        ]
        formatted.append(
            {
                "test_id": f"test-{index}",
                "test_file": test_file,
                "test_function": test_function,
                "status": status,
                "stdout": "",
                "stderr": "",
                "duration_ms": 0,
                "linked_node_ids": linked_node_ids,
            }
        )
    return formatted
