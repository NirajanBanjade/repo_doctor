"""Static JavaScript and TypeScript repository adapter."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from app.analysis.base_adapter import AdapterBase, GraphEdge, GraphNode

logger = logging.getLogger(__name__)

_SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
_SKIP_DIRS = {".git", "node_modules", "dist", "build", "coverage"}
_CLASS_PATTERN = re.compile(r"\b(?:export\s+)?class\s+([A-Za-z_$][\w$]*)")
_FUNCTION_PATTERN = re.compile(
    r"\b(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"
)
_ARROW_PATTERN = re.compile(
    r"\b(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
    r"(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"
)
_IMPORT_PATTERN = re.compile(r"\bimport\s+(?:[\s\S]*?\s+from\s+)?[\"']([^\"']+)[\"']")
_REQUIRE_PATTERN = re.compile(r"\brequire\(\s*[\"']([^\"']+)[\"']\s*\)")


class TypeScriptAdapter(AdapterBase):
    def detect(self, repo_path: str) -> bool:
        for root, directories, files in os.walk(repo_path):
            directories[:] = [
                directory
                for directory in directories
                if not directory.startswith(".") and directory not in _SKIP_DIRS
            ]
            if "package.json" in files:
                return True
        return False

    def extract_nodes(self, repo_path: str) -> list[GraphNode]:
        nodes: list[GraphNode] = []
        for source_file in _iter_source_files(repo_path):
            relative_path = _relative_path(source_file, repo_path)
            source = _read_source(source_file)
            if source is None:
                continue
            nodes.append(
                GraphNode(
                    node_id=relative_path,
                    kind="file",
                    name=relative_path,
                    path=relative_path,
                    line_start=1,
                    line_end=max(1, source.count("\n") + 1),
                    language="typescript",
                )
            )
            for pattern, kind in (
                (_CLASS_PATTERN, "class"),
                (_FUNCTION_PATTERN, "function"),
                (_ARROW_PATTERN, "function"),
            ):
                for match in pattern.finditer(source):
                    line_number = source.count("\n", 0, match.start()) + 1
                    name = match.group(1)
                    nodes.append(
                        GraphNode(
                            node_id=f"{relative_path}::{name}",
                            kind=kind,
                            name=name,
                            path=relative_path,
                            line_start=line_number,
                            line_end=line_number,
                            language="typescript",
                        )
                    )
        return nodes

    def extract_edges(self, repo_path: str) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        known_files = {
            _relative_path(source_file, repo_path)
            for source_file in _iter_source_files(repo_path)
        }
        for source_file in _iter_source_files(repo_path):
            relative_path = _relative_path(source_file, repo_path)
            source = _read_source(source_file)
            if source is None:
                continue
            imports = list(_IMPORT_PATTERN.finditer(source))
            imports.extend(_REQUIRE_PATTERN.finditer(source))
            for match in imports:
                imported_path = match.group(1)
                line_number = source.count("\n", 0, match.start()) + 1
                target_id, evidence_status, note = _import_target(
                    relative_path, imported_path, known_files
                )
                edges.append(
                    GraphEdge(
                        source_id=relative_path,
                        target_id=target_id,
                        relationship="imports",
                        file=relative_path,
                        line=line_number,
                        evidence_status=evidence_status,
                        note=note,
                    )
                )
        return edges


def _iter_source_files(repo_path: str):
    for root, directories, files in os.walk(repo_path):
        directories[:] = [
            directory
            for directory in directories
            if not directory.startswith(".") and directory not in _SKIP_DIRS
        ]
        for filename in sorted(files):
            if Path(filename).suffix in _SOURCE_SUFFIXES:
                yield os.path.join(root, filename)


def _relative_path(source_file: str, repo_path: str) -> str:
    return os.path.relpath(source_file, repo_path).replace(os.sep, "/")


def _read_source(source_file: str) -> str | None:
    try:
        with open(source_file, encoding="utf-8", errors="replace") as file_handle:
            return file_handle.read()
    except OSError as exc:
        logger.warning("typescript_adapter: cannot read %s: %s", source_file, exc)
        return None


def _import_target(
    source_path: str, imported_path: str, known_files: set[str]
) -> tuple[str, str, str | None]:
    if not imported_path.startswith("."):
        return (
            f"external::{imported_path}",
            "inferred",
            f"External package import; target is outside the repository: {imported_path}",
        )

    source_directory = os.path.dirname(source_path)
    normalized = os.path.normpath(os.path.join(source_directory, imported_path))
    candidates = [normalized, *[f"{normalized}{suffix}" for suffix in _SOURCE_SUFFIXES]]
    candidates.extend(
        os.path.join(normalized, f"index{suffix}") for suffix in _SOURCE_SUFFIXES
    )
    for candidate in candidates:
        candidate = candidate.replace(os.sep, "/")
        if candidate in known_files:
            return candidate, "confirmed_static", None
    return (
        normalized.replace(os.sep, "/"),
        "inferred",
        f"Relative import could not be resolved statically: {imported_path}",
    )
