"""Build evidence-backed test scenarios from selected Python graph nodes.

This planner is the offline fallback for the Test Agent.  It only describes
behaviour that is visible in the source AST; it does not infer product rules.
"""

from __future__ import annotations

import ast
import logging
import re
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def build_deterministic_scenarios(
    repo_path: str, selected_nodes: list[dict]
) -> list[dict]:
    """Return deterministic test-plan scenarios for selected Python nodes."""
    scenarios: list[dict] = []
    for node in selected_nodes:
        scenarios.extend(_scenarios_for_node(Path(repo_path), node))
    return scenarios


def _scenarios_for_node(repo_root: Path, node: dict) -> list[dict]:
    relative_path = str(node.get("path") or "")
    source_path = (repo_root / relative_path).resolve()
    try:
        source_path.relative_to(repo_root.resolve())
    except ValueError:
        logger.warning(
            "deterministic_test_planner: path escapes repo: %s", relative_path
        )
        return [_source_contract_scenario(node)]

    if source_path.suffix != ".py" or not source_path.is_file():
        return [_source_contract_scenario(node)]

    try:
        tree = ast.parse(
            source_path.read_text(encoding="utf-8", errors="replace"),
            filename=relative_path,
        )
    except (OSError, SyntaxError):
        logger.warning("deterministic_test_planner: could not parse %s", source_path)
        return [_source_contract_scenario(node)]

    target = _find_target(tree, node)
    if target is None:
        return [_source_contract_scenario(node)]

    scenarios = [_normal_path_scenario(node, target)]
    for item in ast.walk(target):
        if isinstance(item, ast.If):
            scenarios.append(_branch_scenario(node, item))
        elif isinstance(item, ast.Raise):
            scenarios.append(_raise_scenario(node, item))

    route_scenario = _route_contract_scenario(node, target)
    if route_scenario is not None:
        scenarios.append(route_scenario)
    return scenarios


def _find_target(tree: ast.AST, node: dict) -> ast.AST | None:
    name = str(node.get("name") or "")
    if name:
        matches = [
            item
            for item in ast.walk(tree)
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and item.name == name
        ]
        if matches:
            line = int(node.get("line_start") or 0)
            return min(matches, key=lambda item: abs(item.lineno - line))
    return tree if isinstance(tree, ast.Module) else None


def _normal_path_scenario(node: dict, target: ast.AST) -> dict:
    name = str(node.get("name") or node["node_id"])
    return _scenario(
        node,
        line=getattr(target, "lineno", int(node.get("line_start") or 1)),
        label="normal_path",
        name=f"Exercise the normal path of {name}",
        expected=(
            f"{name} completes its explicit non-error path while preserving its "
            "observable return contract."
        ),
        rationale="Every selected component needs a baseline regression scenario.",
    )


def _branch_scenario(node: dict, branch: ast.If) -> dict:
    condition = ast.unparse(branch.test)
    outcomes = [f"condition is true: {condition}"]
    if branch.orelse:
        outcomes.append(f"condition is false: {condition}")
    return _scenario(
        node,
        line=branch.lineno,
        label=f"branch_{branch.lineno}",
        name=f"Cover branch at line {branch.lineno}",
        expected=f"The code follows the intended path when `{condition}` is true.",
        rationale="The source contains an explicit conditional branch.",
        edge_cases=outcomes,
    )


def _raise_scenario(node: dict, raised: ast.Raise) -> dict:
    expression = ast.unparse(raised.exc) if raised.exc is not None else "exception"
    return _scenario(
        node,
        line=raised.lineno,
        label=f"raise_{raised.lineno}",
        name=f"Verify error path at line {raised.lineno}",
        expected=f"Inputs reaching this path raise `{expression}`.",
        rationale="The source explicitly raises an exception on this path.",
    )


def _route_contract_scenario(node: dict, target: ast.AST) -> dict | None:
    if not isinstance(target, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    for decorator in target.decorator_list:
        if not isinstance(decorator, ast.Call) or not isinstance(
            decorator.func, ast.Attribute
        ):
            continue
        method = decorator.func.attr.lower()
        if method not in {"get", "post", "put", "patch", "delete"}:
            continue
        route = ast.unparse(decorator.args[0]) if decorator.args else "configured path"
        status = next(
            (
                ast.unparse(keyword.value)
                for keyword in decorator.keywords
                if keyword.arg == "status_code"
            ),
            "the declared/default success status",
        )
        return _scenario(
            node,
            line=decorator.lineno,
            label="route_contract",
            name=f"Verify {method.upper()} {route} success contract",
            expected=f"A valid request returns {status} and matches the route contract.",
            rationale="The selected function is an explicitly decorated API route.",
        )
    return None


def _source_contract_scenario(node: dict) -> dict:
    name = str(node.get("name") or node["node_id"])
    return _scenario(
        node,
        line=int(node.get("line_start") or 1),
        label="source_contract",
        name=f"Validate source contract for {name}",
        expected=f"The source remains parseable and continues to declare {name}.",
        rationale="No supported behavioral structure was available for static planning.",
    )


def _scenario(
    node: dict,
    *,
    line: int,
    label: str,
    name: str,
    expected: str,
    rationale: str,
    edge_cases: list[str] | None = None,
) -> dict:
    component_id = str(node["node_id"])
    safe_component = _safe_identifier(component_id)
    safe_label = _safe_identifier(label)
    return {
        "scenario_id": str(uuid.uuid4()),
        "name": name,
        "component_id": component_id,
        "source_evidence": f"{node.get('path') or ''}:{line}",
        "expected_behavior": expected,
        "proposed_test_file": (
            f"tests/generated/test_{safe_component}_{safe_label}.py"
        ),
        "proposed_test_function": f"test_{safe_component}_{safe_label}",
        "rationale": rationale,
        "edge_cases": edge_cases or [],
    }


def _safe_identifier(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", value).strip("_") or "scenario"
