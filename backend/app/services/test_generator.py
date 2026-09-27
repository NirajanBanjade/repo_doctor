"""
app/services/test_generator.py

Generate executable pytest files for each approved TestScenario.
Uses a conservative template approach — no LLM at this step.

Decision: the MVP uses deterministic source-contract templates. Bob proposes the
plan but does not write code. Applicable existing tests provide behavioral checks.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_TEST_TEMPLATE = '''\
"""
Auto-generated regression test.
Scenario : {name}
Component: {component_id}
Evidence : {source_evidence}
Expected : {expected_behavior}
"""

import ast
from pathlib import Path


def {func_name}():
    source_path = Path({source_path!r})
    assert source_path.is_file(), f"Expected source file does not exist: {{source_path}}"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    expected_symbol = {symbol_name!r}
    if expected_symbol:
        declarations = {{
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }}
        assert expected_symbol in declarations, (
            f"Expected component {{expected_symbol!r}} was not found in {{source_path}}"
        )
'''


class ApprovalRequiredError(Exception):
    """Raised when test generation is attempted without an approved plan."""


def generated_test_filename(scenario: dict, index: int) -> str:
    """Return a stable, collision-resistant filename for a plan scenario."""
    component_id = str(scenario.get("component_id") or "unknown")
    safe_component = re.sub(r"[^a-zA-Z0-9_]", "_", component_id).strip("_")
    safe_component = safe_component or f"scenario_{index}"
    function_name = str(scenario.get("proposed_test_function") or "")
    safe_function = re.sub(r"[^a-zA-Z0-9_]", "_", function_name).strip("_")
    suffix = safe_function or str(index)
    return f"test_{safe_component}_{suffix}.py"


def generate_test_files(
    plan: dict,
    working_copy_root: str,
) -> list[str]:
    """
    Write one executable pytest source-contract test per scenario into
    working_copy_root/tests/generated/.

    plan must have status == "approved"; raises ApprovalRequiredError otherwise.
    Returns list of absolute paths to generated files.

    Never overwrites files that live outside working_copy_root.
    """
    if plan.get("status") != "approved":
        raise ApprovalRequiredError(
            f"Cannot generate tests: plan {plan.get('plan_id')} status is"
            f" {plan.get('status')!r}, expected 'approved'."
        )

    generated_dir = Path(working_copy_root) / "tests" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for index, scenario in enumerate(plan.get("scenarios", []), start=1):
        component_id: str = scenario.get("component_id", "unknown")
        safe_component = re.sub(r"[^a-zA-Z0-9_]", "_", component_id).strip("_")
        safe_component = safe_component or f"scenario_{index}"
        file_path = generated_dir / generated_test_filename(scenario, index)

        func_name: str = scenario.get("proposed_test_function", "")
        if not func_name or not func_name.startswith("test_"):
            func_name = f"test_{safe_component}"
        func_name = re.sub(r"[^a-zA-Z0-9_]", "_", func_name)

        evidence = str(scenario.get("source_evidence", ""))
        source_path = evidence.rsplit(":", 1)[0] if evidence else ""
        symbol_name = component_id.rsplit("::", 1)[1] if "::" in component_id else ""

        content = _TEST_TEMPLATE.format(
            name=scenario.get("name", ""),
            component_id=component_id,
            source_evidence=scenario.get("source_evidence", ""),
            func_name=func_name,
            expected_behavior=scenario.get("expected_behavior", ""),
            source_path=source_path,
            symbol_name=symbol_name,
        )

        try:
            ast.parse(content, filename=str(file_path))
            file_path.write_text(content, encoding="utf-8")
            written.append(str(file_path))
            logger.info("test_generator: wrote %s", file_path)
        except Exception:
            logger.exception("test_generator: failed to write %s", file_path)

    return written
