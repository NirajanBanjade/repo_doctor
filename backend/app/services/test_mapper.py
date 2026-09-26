"""
app/services/test_mapper.py

For each selected graph node, discover existing pytest test files that
directly exercise the node's function/class.

Returns ExistingTestMapping per node:
  - node_id
  - test_files: list of paths (relative to repo root)
  - coverage_status: "covered" | "indirect" | "no_suitable_test"
"""

from __future__ import annotations

import ast
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExistingTestMapping:
    node_id: str
    test_files: list[str] = field(default_factory=list)
    # "covered" = direct, "indirect" = import only, "no_suitable_test" = none
    coverage_status: str = "no_suitable_test"


def map_tests_to_nodes(
    repo_path: str,
    nodes: list[dict],
) -> list[ExistingTestMapping]:
    """
    For each node, search the repo's tests/ directory for test files that
    import or assert against the node's module path or function name.
    """
    tests_dir = Path(repo_path) / "tests"
    test_files = _collect_test_files(tests_dir) if tests_dir.is_dir() else []

    # Also check root-level test files (test_*.py / *_test.py)
    root_test_files = [
        p
        for p in Path(repo_path).iterdir()
        if p.is_file()
        and p.suffix == ".py"
        and (p.stem.startswith("test_") or p.stem.endswith("_test"))
    ]
    test_files = test_files + root_test_files

    mappings: list[ExistingTestMapping] = []
    for node in nodes:
        mapping = _map_single_node(node, test_files, repo_path)
        mappings.append(mapping)
    return mappings


def _collect_test_files(tests_dir: Path) -> list[Path]:
    result: list[Path] = []
    for root, _dirs, files in os.walk(tests_dir):
        for fname in files:
            if fname.endswith(".py") and (
                fname.startswith("test_") or fname.endswith("_test.py")
            ):
                result.append(Path(root) / fname)
    return result


def _map_single_node(
    node: dict, test_files: list[Path], repo_path: str
) -> ExistingTestMapping:
    node_id: str = node["node_id"]
    func_name: str = node.get("name", "")
    node_path: str = node.get("path", "")

    # derive module name from path (e.g. "payment.py" -> "payment")
    module_name = Path(node_path).stem if node_path else ""

    direct: list[str] = []
    indirect: list[str] = []

    for tf in test_files:
        try:
            source = tf.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(tf))
        except SyntaxError:
            logger.warning("test_mapper: syntax error parsing %s", tf)
            continue
        except Exception:  # noqa: BLE001
            logger.warning("test_mapper: could not read %s", tf)
            continue

        rel_path = (
            str(tf.relative_to(repo_path)) if tf.is_relative_to(repo_path) else str(tf)
        )

        imports_module = _imports_module(tree, module_name)
        asserts_func = (
            _asserts_or_calls_function(tree, func_name) if func_name else False
        )

        if asserts_func:
            direct.append(rel_path)
        elif imports_module:
            indirect.append(rel_path)

    if direct:
        return ExistingTestMapping(
            node_id=node_id,
            test_files=direct,
            coverage_status="covered",
        )
    if indirect:
        return ExistingTestMapping(
            node_id=node_id,
            test_files=indirect,
            coverage_status="indirect",
        )
    return ExistingTestMapping(node_id=node_id)


def _imports_module(tree: ast.AST, module_name: str) -> bool:
    """Return True if the tree imports the given module name."""
    if not module_name:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module_name or alias.name.startswith(
                    module_name + "."
                ):
                    return True
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (
                node.module == module_name or node.module.startswith(module_name + ".")
            )
        ):
            return True
    return False


def _asserts_or_calls_function(tree: ast.AST, func_name: str) -> bool:
    """Return True if the tree contains a Call or mock.patch referencing func_name."""
    if not func_name:
        return False
    for node in ast.walk(tree):
        # Direct call: func_name(...)  or obj.func_name(...)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == func_name:
                return True
            if isinstance(node.func, ast.Attribute) and node.func.attr == func_name:
                return True
        # mock.patch string: "module.func_name"
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and func_name in node.value
        ):
            return True
    return False
