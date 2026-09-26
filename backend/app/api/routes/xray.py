"""
app/api/routes/xray.py

POST /api/v1/sessions/{session_id}/xray       — run X-Ray analysis
GET  /api/v1/sessions/{session_id}/xray/graph — retrieve X-Ray result
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException

from app.analysis.adapter_registry import get_adapter
from app.analysis.graph_builder import build_graph
from app.bob.integration import run_xray_agents
from app.db import evidence_store
from app.services import repo_importer
from app.services import session as session_svc

logger = logging.getLogger(__name__)

router = APIRouter()

_README_NAMES = ("README.md", "README.rst", "README.txt", "README")
_DOC_NAMES = ("CONTRIBUTING.md", "CONTRIBUTING", "docs/setup.md", "docs/index.md")


@router.post("/{session_id}/xray", status_code=202)
async def run_xray(session_id: str) -> dict:
    """
    Trigger stack detection, adapter extraction, graph build, and Bob agents.
    Returns immediately with status; use GET /xray/graph to read results.
    """
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    repo_path = s["repo_path"]
    if not os.path.isdir(repo_path):
        raise HTTPException(
            status_code=422, detail=f"repo_path is not a directory: {repo_path}"
        )

    session_svc.update_status(session_id, "xray_running")

    try:
        # 1. Stack detection
        stack = repo_importer.detect_stack(repo_path)
        warnings: list[str] = []

        # 2. Adapter dispatch
        adapter = get_adapter(stack["language"])
        if adapter is None:
            warnings.append(
                f"no_adapter: no adapter available for language '{stack['language']}'"
            )
            nodes, edges = [], []
        else:
            nodes = adapter.extract_nodes(repo_path)
            edges = adapter.extract_edges(repo_path)

        # 3. Build + persist graph
        build_graph(session_id, nodes, edges)

        # 4. Bob agents (parallel, graceful degradation)
        node_dicts = [
            {
                "node_id": n.node_id,
                "name": n.name,
                "path": n.path,
                "line_start": n.line_start,
                "line_end": n.line_end,
            }
            for n in nodes[:100]  # cap payload size
        ]
        readme_excerpt = _read_excerpt(repo_path, _README_NAMES)
        doc_files = {
            name: _read_file(os.path.join(repo_path, name))
            for name in _DOC_NAMES
            if os.path.exists(os.path.join(repo_path, name))
        }
        await run_xray_agents(session_id, node_dicts, stack, readme_excerpt, doc_files)

        # 5. Update session status
        session_svc.update_status(session_id, "xray_complete", stack=stack)

        return {
            "session_id": session_id,
            "status": "xray_complete",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "warnings": warnings,
        }

    except Exception as exc:
        logger.exception("xray: unhandled error session=%s", session_id)
        session_svc.update_status(session_id, "error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{session_id}/xray/graph")
async def get_xray_graph(session_id: str) -> dict:
    """Return the stored X-Ray graph for the session."""
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    raw_nodes = evidence_store.get_nodes(session_id)
    raw_edges = evidence_store.get_edges(session_id)

    nodes = [_serialize_node(r) for r in raw_nodes]
    edges = [_serialize_edge(r) for r in raw_edges]

    # Collect any warnings persisted in bob_outputs with parsed_ok=False
    warnings: list[str] = []
    if not nodes:
        warnings.append("no_nodes: graph is empty — X-Ray may not have run yet")

    return {
        "session_id": session_id,
        "nodes": nodes,
        "edges": edges,
        "architecture_findings": None,  # populated by Bob when available
        "documentation_findings": None,
        "warnings": warnings,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _read_excerpt(repo_path: str, names: tuple, max_chars: int = 2000) -> str:
    for name in names:
        fpath = os.path.join(repo_path, name)
        if os.path.exists(fpath):
            return _read_file(fpath)[:max_chars]
    return ""


def _read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _serialize_node(r) -> dict:
    m = dict(r)
    return {
        "node_id": m["node_id"],
        "kind": m["kind"],
        "name": m["name"],
        "path": m["path"],
        "line_start": m["line_start"],
        "line_end": m["line_end"],
        "language": m["language"],
        "summary": m.get("summary"),
        "key_module": bool(m.get("key_module", False)),
    }


def _serialize_edge(r) -> dict:
    m = dict(r)
    return {
        "edge_id": m["edge_id"],
        "source_id": m["source_id"],
        "target_id": m["target_id"],
        "relationship": m["relationship"],
        "file": m["file"],
        "line": m["line"],
        "evidence_status": m["evidence_status"],
        "note": m.get("note"),
    }
