"""
app/analysis/graph_builder.py

Merges adapter output into a NetworkX DiGraph, annotates top-5 degree nodes,
and persists to the SQLite evidence store.
See ARCHITECTURE.md §5 and docs/features/01-repository-xray.md.
"""

from __future__ import annotations

import logging

import networkx as nx

from app.analysis.base_adapter import GraphEdge, GraphNode
from app.db import evidence_store

logger = logging.getLogger(__name__)

_TOP_KEY_MODULES = 5


def build_graph(
    session_id: str,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    db_url: str = "sqlite:///./repodoc.db",
) -> nx.DiGraph:
    """
    Build NetworkX DiGraph, annotate key modules (top-5 by degree),
    persist nodes and edges, and return the graph.
    """
    g: nx.DiGraph = nx.DiGraph()

    for n in nodes:
        g.add_node(n.node_id, **_node_attrs(n))

    for e in edges:
        g.add_edge(e.source_id, e.target_id, **_edge_attrs(e))

    # Annotate top-5 highest-degree nodes as key_module=True
    if nodes:
        centrality = nx.degree_centrality(g)
        top = sorted(centrality, key=centrality.get, reverse=True)[:_TOP_KEY_MODULES]
        top_set = set(top)
        for n in nodes:
            if n.node_id in top_set:
                n.key_module = True
                if n.node_id in g:
                    g.nodes[n.node_id]["key_module"] = True

    evidence_store.save_nodes(session_id, nodes, db_url=db_url)
    evidence_store.save_edges(session_id, edges, db_url=db_url)

    logger.info(
        "graph_builder: session=%s nodes=%d edges=%d",
        session_id,
        len(nodes),
        len(edges),
    )
    return g


def _node_attrs(n: GraphNode) -> dict:
    return {
        "kind": n.kind,
        "name": n.name,
        "path": n.path,
        "line_start": n.line_start,
        "line_end": n.line_end,
        "language": n.language,
        "summary": n.summary,
        "key_module": n.key_module,
    }


def _edge_attrs(e: GraphEdge) -> dict:
    return {
        "relationship": e.relationship,
        "file": e.file,
        "line": e.line,
        "evidence_status": e.evidence_status,
        "note": e.note,
    }
