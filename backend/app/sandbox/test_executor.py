"""
app/sandbox/test_executor.py

Run pytest inside the Docker sandbox for a test plan and parse results.
See AGENTS.md §9 and docs/features/05-radius-test-generator.md §Sandbox execution.
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_DOCKER_IMAGE = "repodoc-sandbox"
_CPU_LIMIT = "1"
_MEMORY_LIMIT = "512m"
_TIMEOUT_S = 120


async def run_tests(
    repo_path: str,
    working_copy_root: str,
    existing_test_files: list[str],
    generated_dir: str,
) -> dict:
    """
    Execute pytest inside Docker sandbox over existing_test_files + generated_dir.

    Returns dict with keys:
      stdout, stderr, exit_code, infrastructure_error, per_test (list of
      {nodeid, outcome}), component_statuses (empty list — caller maps these).
    """
    # Write a temp json-report output path inside container
    report_path_host = Path(tempfile.mktemp(suffix=".json"))

    # Build file list: de-dup, relative paths inside container
    test_args: list[str] = list(dict.fromkeys(existing_test_files))
    generated_path = Path(generated_dir)
    if generated_path.is_dir() and list(generated_path.rglob("test_*.py")):
        test_args.append(str(generated_path))

    if not test_args:
        return _infra_error("No test files to run.")

    # Map paths: existing files live under repo_path (/repo), generated under /working_copy
    container_test_args: list[str] = []
    for arg in test_args:
        p = Path(arg)
        if p.is_absolute():
            # generated files or absolute paths
            try:
                rel = p.relative_to(working_copy_root)
                container_test_args.append(f"/working_copy/{rel}")
            except ValueError:
                try:
                    rel = p.relative_to(repo_path)
                    container_test_args.append(f"/repo/{rel}")
                except ValueError:
                    container_test_args.append(str(p))
        else:
            container_test_args.append(f"/repo/{arg}")

    report_container = "/tmp/pytest_report.json"
    pytest_cmd = (
        "pytest "
        + " ".join(container_test_args)
        + f" --json-report --json-report-file={report_container} --tb=short -q"
    )

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        f"--cpus={_CPU_LIMIT}",
        f"--memory={_MEMORY_LIMIT}",
        "--network=none",
        "--volume",
        f"{repo_path}:/repo:ro",
        "--volume",
        f"{working_copy_root}:/working_copy:ro",
        "--volume",
        f"{report_path_host.parent}:/tmp",
        "--workdir",
        "/repo",
        _DOCKER_IMAGE,
        "sh",
        "-c",
        pytest_cmd,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=_TIMEOUT_S
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            logger.warning("test_executor: sandbox timeout after %ss", _TIMEOUT_S)
            return _infra_error(f"Sandbox timeout after {_TIMEOUT_S}s")

        exit_code = proc.returncode
        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")

        # Parse json-report if available
        per_test: list[dict] = []
        if report_path_host.exists():
            try:
                report = json.loads(report_path_host.read_text())
                for t in report.get("tests", []):
                    per_test.append(
                        {
                            "nodeid": t.get("nodeid", ""),
                            "outcome": t.get("outcome", "unknown"),
                        }
                    )
            except Exception:  # noqa: BLE001
                logger.warning("test_executor: could not parse json-report")

        # Non-test infrastructure failure: container exited > 0 for non-test reasons
        # (exit code 1 = tests failed, 5 = no tests collected — both are NOT infra errors)
        infra_error = exit_code is not None and exit_code not in (0, 1, 2, 4, 5)

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "infrastructure_error": infra_error,
            "per_test": per_test,
            "component_statuses": [],
        }

    except Exception as exc:
        logger.exception("test_executor: unexpected error")
        return _infra_error(str(exc))
    finally:
        if report_path_host.exists():
            report_path_host.unlink(missing_ok=True)


def build_component_statuses(
    scenarios: list[dict],
    per_test: list[dict],
    generated_files: list[str],
    infrastructure_error: bool,
) -> list[dict]:
    """
    Map per-test results back to component_ids from the test plan.

    component_id → status:
      covered_passed  — ≥1 test, all passed
      covered_failed  — ≥1 test, at least one failed
      unexecuted      — test was generated but infra error prevented running
      no_suitable_test — no test exists and no generated test
    """
    # Build map: component_id -> list of outcomes
    component_outcomes: dict[str, list[str]] = {}
    for scenario in scenarios:
        component_id = scenario.get("component_id", "")
        func_name = scenario.get("proposed_test_function", "")
        if not component_id:
            continue
        component_outcomes.setdefault(component_id, [])
        # Find matching test results by function name
        for t in per_test:
            if func_name and func_name in t.get("nodeid", ""):
                component_outcomes[component_id].append(t["outcome"])

    statuses: list[dict] = []
    for scenario in scenarios:
        component_id = scenario.get("component_id", "")
        if not component_id:
            continue

        safe = component_id.replace("::", "_").replace("/", "_").replace(".", "_")
        has_generated = any(safe in gf for gf in generated_files)
        outcomes = component_outcomes.get(component_id, [])

        if not outcomes and infrastructure_error and has_generated:
            status = "unexecuted"
        elif not outcomes:
            status = "no_suitable_test"
        elif any(o in ("failed", "error") for o in outcomes):
            status = "covered_failed"
        else:
            status = "covered_passed"

        statuses.append({"component_id": component_id, "status": status})

    return statuses


def _infra_error(msg: str) -> dict:
    return {
        "stdout": "",
        "stderr": msg,
        "exit_code": None,
        "infrastructure_error": True,
        "per_test": [],
        "component_statuses": [],
    }
