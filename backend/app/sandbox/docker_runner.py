"""
app/sandbox/docker_runner.py

Docker container lifecycle for Environment Doctor.
Each run uses a fresh, resource-limited, network-isolated container.
See AGENTS.md §9 and docs/features/02-environment-doctor.md.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.environment_doctor import SetupPlan, SetupStep

logger = logging.getLogger(__name__)

_DOCKER_IMAGE = "repodoc-sandbox"
_CPU_LIMIT = "1"
_MEMORY_LIMIT = "512m"
_NETWORK = "none"


# ── Public API ────────────────────────────────────────────────────────────────


async def run_setup_plan(
    plan: SetupPlan,
    repo_path: str,
) -> list[dict]:
    """
    Execute each SetupStep from *plan* sequentially inside a fresh Docker
    container.  Returns a list of result dicts (one per step) with keys:
      step_id, command, status, exit_code, stdout, stderr,
      started_at, finished_at.

    Status values:
      verified            — exit code matched expected_exit_code
      failed              — exit code did not match
      blocked             — earlier step failed; not attempted
      infrastructure_error — timeout, OOM, or unexpected Docker error
    """
    results: list[dict] = []
    failed = False

    for step in plan.steps:
        if failed:
            results.append(_blocked_result(step))
            continue

        result = await _run_step(step, repo_path)
        results.append(result)
        if result["status"] != "verified":
            failed = True

    return results


# ── Internal helpers ──────────────────────────────────────────────────────────


async def _run_step(step: SetupStep, repo_path: str) -> dict:
    started_at = datetime.now(timezone.utc)
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        f"--cpus={_CPU_LIMIT}",
        f"--memory={_MEMORY_LIMIT}",
        f"--network={_NETWORK}",
        "--volume",
        f"{repo_path}:/repo:ro",
        "--workdir",
        "/repo",
        _DOCKER_IMAGE,
        "sh",
        "-c",
        step.command,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=step.timeout_s
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            finished_at = datetime.now(timezone.utc)
            logger.warning(
                "docker_runner: step timeout step_id=%s command=%r",
                step.step_id,
                step.command,
            )
            return {
                "step_id": step.step_id,
                "command": step.command,
                "status": "infrastructure_error",
                "exit_code": None,
                "stdout": "",
                "stderr": f"Timeout after {step.timeout_s}s",
                "started_at": started_at,
                "finished_at": finished_at,
            }

        exit_code = proc.returncode
        finished_at = datetime.now(timezone.utc)
        status = "verified" if exit_code == step.expected_exit_code else "failed"
        return {
            "step_id": step.step_id,
            "command": step.command,
            "status": status,
            "exit_code": exit_code,
            "stdout": stdout_bytes.decode("utf-8", errors="replace"),
            "stderr": stderr_bytes.decode("utf-8", errors="replace"),
            "started_at": started_at,
            "finished_at": finished_at,
        }

    except Exception as exc:
        finished_at = datetime.now(timezone.utc)
        logger.exception("docker_runner: unexpected error step_id=%s", step.step_id)
        return {
            "step_id": step.step_id,
            "command": step.command,
            "status": "infrastructure_error",
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "started_at": started_at,
            "finished_at": finished_at,
        }


def _blocked_result(step: SetupStep) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "step_id": step.step_id,
        "command": step.command,
        "status": "blocked",
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "started_at": now,
        "finished_at": now,
    }
