"""
app/api/routes/impact.py

POST /api/v1/sessions/{session_id}/impact       — run BFS impact analysis
GET  /api/v1/sessions/{session_id}/impact/graph — retrieve latest impact result
"""

from __future__ import annotations

import logging
import uuid

import networkx as nx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from app.analysis.impact_engine import compute_impact, parse_diff_symbols
from app.bob.integration import run_impact_agent
from app.db import evidence_store
from app.services import session as session_svc
from app.services.feature_wiki import parse_feature_wiki

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request schema ─────────────────────────────────────────────────────────────


class ImpactRequest(BaseModel):
    symbol_id: str | None = None
    feature_id: str | None = None
    file_path: str | None = None
    git_diff: str | None = None
    change_description: str | None = None
    depth: int = 1

    @model_validator(mode="after")
    def _check_exactly_one_origin(self) -> ImpactRequest:
        origins = [self.symbol_id, self.feature_id, self.file_path, self.git_diff]
        if sum(value is not None for value in origins) != 1:
            raise ValueError(
                "Provide exactly one of symbol_id, feature_id, file_path, or git_diff."
            )
        if self.depth not in (1, 2, 3):
            raise ValueError("depth must be 1, 2, or 3.")
        return self


# ── Helpers ────────────────────────────────────────────────────────────────────


def _load_nx_graph(session_id: str, db_url: str) -> nx.DiGraph:
    """Reconstruct a NetworkX DiGraph from persisted nodes/edges."""
    raw_nodes = evidence_store.get_nodes(session_id, db_url=db_url)
    raw_edges = evidence_store.get_edges(session_id, db_url=db_url)
    g: nx.DiGraph = nx.DiGraph()
    for n in raw_nodes:
        g.add_node(n["node_id"], **n)
    for e in raw_edges:
        g.add_edge(e["source_id"], e["target_id"], **e)
    return g


def _resolve_origins(
    req: ImpactRequest,
    raw_nodes: list[dict],
) -> tuple[list[str], list[str]]:
    """
    Return (origin_ids, unresolved_symbols).
    For symbol_id: direct lookup.
    For git_diff: parse symbol names and match against graph_nodes.
    """
    node_ids = {n["node_id"] for n in raw_nodes}

    direct_id = req.symbol_id
    if req.file_path is not None:
        direct_id = f"file:{req.file_path}"
    if direct_id is not None:
        if direct_id in node_ids:
            return [direct_id], []
        return [], [direct_id]

    # git_diff path
    symbols = list(dict.fromkeys(parse_diff_symbols(req.git_diff or "")))  # dedup
    origins: list[str] = []
    unresolved: list[str] = []
    name_to_ids: dict[str, list[str]] = {}
    for n in raw_nodes:
        name_to_ids.setdefault(n["name"], []).append(n["node_id"])

    for sym in symbols:
        matched = name_to_ids.get(sym, [])
        if matched:
            origins.extend(matched)
        else:
            unresolved.append(sym)
            logger.warning("impact: unresolved_symbol '%s' not found in graph", sym)
    return origins, unresolved


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.post("/{session_id}/impact", status_code=202)
async def run_impact(session_id: str, body: ImpactRequest) -> dict:
    """
    Run BFS impact analysis from a symbol or git diff, then invoke Impact Agent.
    Returns the full ImpactRunResult with Bob annotations (if available).
    """
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    raw_nodes = evidence_store.get_nodes(session_id)
    raw_edges = evidence_store.get_edges(session_id)

    if not raw_nodes:
        raise HTTPException(status_code=422, detail="No graph found — run X-Ray first.")

    architecture_path = (s.get("stack") or {}).get("architecture_path")
    architecture = (
        parse_feature_wiki(s["repo_path"], architecture_path)
        if architecture_path
        else None
    )
    primary_feature = None
    external_features: list[dict] = []
    if body.feature_id and architecture:
        primary_feature = next(
            (f for f in architecture.features if f.feature_id == body.feature_id), None
        )
        if primary_feature is None:
            raise HTTPException(status_code=422, detail="Feature not found in wiki")
        origin_ids = [f"file:{path}" for path in primary_feature.files]
        unresolved = []
        by_id = {f.feature_id: f for f in architecture.features}
        external_features = [
            {
                "feature_id": feature_id,
                "name": by_id[feature_id].name,
                "reason": "Connected at the primary feature boundary",
            }
            for feature_id in primary_feature.connected_feature_ids
            if feature_id in by_id
        ]
    else:
        origin_ids, unresolved = _resolve_origins(body, raw_nodes)
    warnings: list[str] = []

    if not origin_ids:
        warnings.append("no_origin: no matching graph nodes found for the given input")

    # Build in-memory graph and run BFS
    g = _load_nx_graph(session_id, "sqlite:///./repodoc.db")
    bfs = compute_impact(g, origin_ids, body.depth)

    # Include every relationship between impacted files. With a feature as the
    # origin, all of its files are depth-zero roots, so a traversal-only edge
    # list would incorrectly render the documented feature flow as disconnected.
    impacted_ids = set(bfs.visited)
    traversed_edge_rows = [
        e
        for e in raw_edges
        if e["source_id"] in impacted_ids and e["target_id"] in impacted_ids
    ]

    # Assemble BFS node payloads for Bob
    node_map = {n["node_id"]: n for n in raw_nodes}
    bfs_node_payloads = [
        {
            "node_id": nid,
            "depth_level": d,
            "name": node_map[nid]["name"] if nid in node_map else nid,
            "path": node_map[nid]["path"] if nid in node_map else "",
        }
        for nid, d in bfs.visited.items()
    ]
    bfs_edge_payloads = [
        {
            "source_id": e["source_id"],
            "target_id": e["target_id"],
            "relationship": e["relationship"],
            "evidence_status": e["evidence_status"],
        }
        for e in traversed_edge_rows
    ]

    # Impact Agent (graceful degradation)
    annotations_result = await run_impact_agent(
        session_id=session_id,
        origin_ids=origin_ids,
        bfs_nodes=bfs_node_payloads,
        bfs_edges=bfs_edge_payloads,
        change_description=body.change_description,
    )

    run_id = str(uuid.uuid4())
    evidence_store.save_impact_run(
        session_id=session_id,
        run_id=run_id,
        origin_ids=origin_ids,
        depth=body.depth,
        node_depths=bfs.visited,
        change_description=body.change_description,
        unresolved_symbols=unresolved,
    )
    session_svc.update_status(session_id, "impact_complete")

    annotations = (
        [a.model_dump() for a in annotations_result.annotations]
        if annotations_result
        else []
    )

    impact_nodes_out = [
        {
            "node_id": nid,
            "depth_level": d,
            "node": {
                k: v
                for k, v in (node_map.get(nid) or {}).items()
                if k not in ("id", "session_id")
            },
            "existing_tests": [],
        }
        for nid, d in bfs.visited.items()
    ]

    return {
        "run_id": run_id,
        "session_id": session_id,
        "origin_ids": origin_ids,
        "depth": body.depth,
        "change_description": body.change_description,
        "nodes": impact_nodes_out,
        "edges": [
            {k: v for k, v in e.items() if k not in ("id", "session_id")}
            for e in traversed_edge_rows
        ],
        "annotations": annotations,
        "unresolved_symbols": unresolved,
        "warnings": warnings,
        "bounded_analysis": True,
        "bounded_analysis_note": (
            f"Analysis bounded to {body.depth} hop(s) from origin. "
            "Results are not exhaustive."
        ),
        "primary_feature": (
            {"feature_id": primary_feature.feature_id, "name": primary_feature.name}
            if primary_feature
            else None
        ),
        "external_feature_suggestions": external_features,
    }


@router.get("/{session_id}/impact/graph")
async def get_impact_graph(session_id: str) -> dict:
    """Return the most recent impact run for this session."""
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    run = evidence_store.get_latest_impact_run(session_id)
    if run is None:
        return {
            "session_id": session_id,
            "run": None,
            "warnings": ["no_impact_run: impact analysis has not been run yet"],
        }

    nodes_rows = evidence_store.get_impact_nodes(run["run_id"])
    raw_nodes = evidence_store.get_nodes(session_id)
    raw_edges = evidence_store.get_edges(session_id)
    node_map = {n["node_id"]: n for n in raw_nodes}
    impact_ids = {row["node_id"] for row in nodes_rows}

    impact_nodes_out = [
        {
            "node_id": r["node_id"],
            "depth_level": r["depth_level"],
            "node": {
                k: v
                for k, v in (node_map.get(r["node_id"]) or {}).items()
                if k not in ("id", "session_id")
            },
            "existing_tests": [],
        }
        for r in nodes_rows
    ]

    architecture_path = (s.get("stack") or {}).get("architecture_path")
    primary_feature = None
    external_features: list[dict] = []
    if architecture_path:
        architecture = parse_feature_wiki(s["repo_path"], architecture_path)
        origins = set(run["origin_ids"])
        primary_feature = next(
            (
                feature
                for feature in architecture.features
                if origins
                and origins.issubset({f"file:{path}" for path in feature.files})
            ),
            None,
        )
        if primary_feature:
            by_id = {feature.feature_id: feature for feature in architecture.features}
            external_features = [
                {
                    "feature_id": feature_id,
                    "name": by_id[feature_id].name,
                    "reason": "Connected at the primary feature boundary",
                }
                for feature_id in primary_feature.connected_feature_ids
                if feature_id in by_id
            ]

    return {
        "session_id": session_id,
        "run_id": run["run_id"],
        "origin_ids": run["origin_ids"],
        "depth": run["depth"],
        "change_description": run["change_description"],
        "nodes": impact_nodes_out,
        "edges": [
            {k: v for k, v in edge.items() if k not in ("id", "session_id")}
            for edge in raw_edges
            if edge["source_id"] in impact_ids and edge["target_id"] in impact_ids
        ],
        "annotations": [],
        "unresolved_symbols": run["unresolved_symbols"],
        "warnings": [],
        "bounded_analysis": True,
        "bounded_analysis_note": (
            f"Analysis bounded to {run['depth']} hop(s) from origin. "
            "Results are not exhaustive."
        ),
        "primary_feature": (
            {"feature_id": primary_feature.feature_id, "name": primary_feature.name}
            if primary_feature
            else None
        ),
        "external_feature_suggestions": external_features,
    }
