"""
app/api/routes/environment.py

POST /api/v1/sessions/{session_id}/environment/run   — run setup sequence
POST /api/v1/sessions/{session_id}/environment/fix   — apply approved fix + re-run
GET  /api/v1/sessions/{session_id}/environment/checks — list check results
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.bob.integration import run_environment_agent
from app.db import evidence_store
from app.sandbox.docker_runner import run_setup_plan
from app.services import session as session_svc
from app.services.environment_doctor import build_setup_plan

logger = logging.getLogger(__name__)

router = APIRouter()

_README_NAMES = ("README.md", "README.rst", "README.txt", "README")


# ── Request/response models ───────────────────────────────────────────────────


class FixRequest(BaseModel):
    step_id: str
    fix_description: str
    patch_content: str | None = None
    approval: bool = False


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/{session_id}/environment/run", status_code=202)
async def run_environment(session_id: str) -> dict:
    """
    Parse README setup commands, run them in a Docker container,
    persist per-step results, and invoke the Environment Agent for
    any failed step.
    """
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    repo_path = s["repo_path"]
    if not os.path.isdir(repo_path):
        raise HTTPException(
            status_code=422, detail=f"repo_path is not a directory: {repo_path}"
        )

    readme_content = _read_readme(repo_path)
    plan = build_setup_plan(readme_content)

    if not plan.steps:
        return {
            "session_id": session_id,
            "status": "no_steps",
            "steps": [],
            "warnings": ["no_steps: no setup commands found in README"],
        }

    # Determine next run_number
    existing = evidence_store.get_environment_checks(session_id)
    run_number = max((r["run_number"] for r in existing), default=0) + 1

    results = await run_setup_plan(plan, repo_path)

    language = (s.get("stack") or {}).get("language", "unknown")

    for result in results:
        evidence_store.save_environment_check(
            session_id=session_id,
            step_id=result["step_id"],
            command=result["command"],
            status=result["status"],
            run_number=run_number,
            exit_code=result.get("exit_code"),
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            started_at=result.get("started_at"),
            finished_at=result.get("finished_at"),
        )
        # Invoke Environment Agent for the first failed step
        if result["status"] == "failed":
            await run_environment_agent(
                session_id=session_id,
                failed_command=result["command"],
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                readme_excerpt=readme_content[:2000],
                language=language,
            )

    serialized = [_serialize_check(r, run_number) for r in results]
    overall = _overall_status(results)
    return {
        "session_id": session_id,
        "status": overall,
        "run_number": run_number,
        "steps": serialized,
        "warnings": [],
    }


@router.post("/{session_id}/environment/fix", status_code=202)
async def apply_fix(session_id: str, body: FixRequest) -> dict:
    """
    Apply an approved fix patch to the working copy, then re-run the
    full setup sequence.  Requires approval=true in the request body.
    """
    if not body.approval:
        raise HTTPException(
            status_code=400,
            detail="approval must be true to apply a fix",
        )

    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    repo_path = s["repo_path"]
    if not os.path.isdir(repo_path):
        raise HTTPException(
            status_code=422, detail=f"repo_path is not a directory: {repo_path}"
        )

    # Apply patch to working copy if provided
    if body.patch_content:
        _apply_patch(repo_path, body.patch_content)

    # Re-run the full setup sequence
    readme_content = _read_readme(repo_path)
    plan = build_setup_plan(readme_content)

    existing = evidence_store.get_environment_checks(session_id)
    run_number = max((r["run_number"] for r in existing), default=0) + 1

    results = await run_setup_plan(plan, repo_path)
    language = (s.get("stack") or {}).get("language", "unknown")

    for result in results:
        evidence_store.save_environment_check(
            session_id=session_id,
            step_id=result["step_id"],
            command=result["command"],
            status=result["status"],
            run_number=run_number,
            exit_code=result.get("exit_code"),
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            started_at=result.get("started_at"),
            finished_at=result.get("finished_at"),
        )
        if result["status"] == "failed":
            await run_environment_agent(
                session_id=session_id,
                failed_command=result["command"],
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                readme_excerpt=readme_content[:2000],
                language=language,
            )

    serialized = [_serialize_check(r, run_number) for r in results]
    overall = _overall_status(results)
    return {
        "session_id": session_id,
        "status": overall,
        "run_number": run_number,
        "steps": serialized,
        "fix_applied": bool(body.patch_content),
        "warnings": [],
    }


@router.get("/{session_id}/environment/checks")
async def get_checks(session_id: str, run_number: int | None = None) -> dict:
    """Return persisted environment check results for this session."""
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    rows = evidence_store.get_environment_checks(session_id, run_number=run_number)
    steps = [
        {
            "step_id": r["step_id"],
            "command": r["command"],
            "status": r["status"],
            "exit_code": r["exit_code"],
            "stdout": r["stdout"],
            "stderr": r["stderr"],
            "run_number": r["run_number"],
            "started_at": r["started_at"].isoformat() if r["started_at"] else None,
            "finished_at": r["finished_at"].isoformat() if r["finished_at"] else None,
        }
        for r in rows
    ]
    return {"session_id": session_id, "steps": steps}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _read_readme(repo_path: str) -> str:
    for name in _README_NAMES:
        fpath = os.path.join(repo_path, name)
        if os.path.exists(fpath):
            try:
                with open(fpath, encoding="utf-8", errors="replace") as fh:
                    return fh.read()
            except OSError:
                pass
    return ""


def _apply_patch(repo_path: str, patch_content: str) -> None:
    """Write a unified diff patch to the working copy using the `patch` utility."""
    import subprocess

    result = subprocess.run(
        ["patch", "-p1", "--directory", repo_path],
        input=patch_content.encode(),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        logger.warning(
            "environment/fix: patch command exited %d: %s",
            result.returncode,
            result.stderr.decode(errors="replace"),
        )


def _serialize_check(result: dict, run_number: int) -> dict:
    return {
        "step_id": result["step_id"],
        "command": result["command"],
        "status": result["status"],
        "exit_code": result.get("exit_code"),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "run_number": run_number,
        "started_at": (
            result["started_at"].isoformat() if result.get("started_at") else None
        ),
        "finished_at": (
            result["finished_at"].isoformat() if result.get("finished_at") else None
        ),
    }


def _overall_status(results: list[dict]) -> str:
    statuses = {r["status"] for r in results}
    if "infrastructure_error" in statuses:
        return "infrastructure_error"
    if "failed" in statuses:
        return "failed"
    if "blocked" in statuses:
        return "partial"
    return "verified"
