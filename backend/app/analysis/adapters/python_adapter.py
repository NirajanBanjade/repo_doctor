"""
app/analysis/adapters/python_adapter.py

Python language adapter. Uses stdlib ast to extract nodes and edges.
See docs/features/01-repository-xray.md and AGENTS.md §7.
"""

from __future__ import annotations

import ast
import logging
import os
from pathlib import Path

from app.analysis.base_adapter import AdapterBase, GraphEdge, GraphNode

logger = logging.getLogger(__name__)

_DYNAMIC_CALLS = {"getattr", "eval", "exec", "__import__", "importlib"}


class PythonAdapter(AdapterBase):
    def detect(self, repo_path: str) -> bool:
        for marker in ("pyproject.toml", "setup.py", "requirements.txt"):
            if os.path.exists(os.path.join(repo_path, marker)):
                return True
        # Fallback: any .py file at root
        return any(Path(repo_path).glob("*.py"))

    def extract_nodes(self, repo_path: str) -> list[GraphNode]:
        nodes: list[GraphNode] = []
        for py_file in _iter_python_files(repo_path):
            rel = os.path.relpath(py_file, repo_path)
            tree = _safe_parse(py_file)
            if tree is None:
                continue
            # File-level module node
            lines = _count_lines(py_file)
            nodes.append(
                GraphNode(
                    node_id=_module_id(rel),
                    kind="module",
                    name=rel,
                    path=rel,
                    line_start=1,
                    line_end=lines,
                    language="python",
                )
            )
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    nodes.append(
                        GraphNode(
                            node_id=_node_id(rel, node.name),
                            kind="class",
                            name=node.name,
                            path=rel,
                            line_start=node.lineno,
                            line_end=_end_line(node),
                            language="python",
                        )
                    )
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    nodes.append(
                        GraphNode(
                            node_id=_node_id(rel, node.name),
                            kind="function",
                            name=node.name,
                            path=rel,
                            line_start=node.lineno,
                            line_end=_end_line(node),
                            language="python",
                        )
                    )
        return nodes

    def extract_edges(self, repo_path: str) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for py_file in _iter_python_files(repo_path):
            rel = os.path.relpath(py_file, repo_path)
            tree = _safe_parse(py_file)
            if tree is None:
                continue
            src_id = _module_id(rel)
            for node in ast.walk(tree):
                # Import edges
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        edges.append(
                            GraphEdge(
                                source_id=src_id,
                                target_id=_module_id(
                                    alias.name.replace(".", "/") + ".py"
                                ),
                                relationship="imports",
                                file=rel,
                                line=node.lineno,
                                evidence_status="confirmed_static",
                            )
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        target = node.module.replace(".", "/") + ".py"
                        edges.append(
                            GraphEdge(
                                source_id=src_id,
                                target_id=_module_id(target),
                                relationship="imports",
                                file=rel,
                                line=node.lineno,
                                evidence_status="confirmed_static",
                            )
                        )
                # Class inheritance edges
                elif isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        base_name = _attr_name(base)
                        if base_name:
                            edges.append(
                                GraphEdge(
                                    source_id=_node_id(rel, node.name),
                                    target_id=base_name,
                                    relationship="inherits",
                                    file=rel,
                                    line=node.lineno,
                                    evidence_status="confirmed_static",
                                )
                            )
                # Dynamic call detection — emit as inferred
                elif isinstance(node, ast.Call):
                    fn_name = _attr_name(node.func)
                    if fn_name in _DYNAMIC_CALLS:
                        edges.append(
                            GraphEdge(
                                source_id=src_id,
                                target_id=f"dynamic::{fn_name}",
                                relationship="calls",
                                file=rel,
                                line=node.lineno,
                                evidence_status="inferred",
                                note=f"Dynamic call via {fn_name}; target cannot be statically resolved",
                            )
                        )
        return edges


# ── Helpers ───────────────────────────────────────────────────────────────────


def _iter_python_files(repo_path: str):
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden dirs and common non-source dirs
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d not in ("__pycache__", "node_modules", ".git")
        ]
        for fname in files:
            if fname.endswith(".py"):
                yield os.path.join(root, fname)


def _safe_parse(py_file: str) -> ast.AST | None:
    try:
        with open(py_file, encoding="utf-8", errors="replace") as fh:
            source = fh.read()
        return ast.parse(source, filename=py_file)
    except SyntaxError as exc:
        logger.warning(
            "python_adapter: skipping %s due to SyntaxError: %s", py_file, exc
        )
        return None
    except OSError as exc:
        logger.warning("python_adapter: cannot read %s: %s", py_file, exc)
        return None


def _module_id(rel_path: str) -> str:
    return rel_path.replace("\\", "/")


def _node_id(rel_path: str, name: str) -> str:
    return f"{rel_path.replace(chr(92), '/')}::{name}"


def _end_line(node: ast.AST) -> int:
    return getattr(node, "end_lineno", node.lineno)


def _count_lines(path: str) -> int:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 1


def _attr_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""
