"""
tests/test_graph_builder.py

Unit tests for graph_builder: NetworkX DiGraph construction,
key_module annotation (top-5 degree), and persistence.
"""

from __future__ import annotations

from app.analysis.base_adapter import GraphEdge, GraphNode
from app.analysis.graph_builder import build_graph


def _make_node(nid: str, kind: str = "function") -> GraphNode:
    return GraphNode(
        node_id=nid,
        kind=kind,
        name=nid,
        path="a.py",
        line_start=1,
        line_end=5,
        language="python",
    )


def _make_edge(src: str, tgt: str) -> GraphEdge:
    return GraphEdge(
        source_id=src,
        target_id=tgt,
        relationship="imports",
        file="a.py",
        line=1,
    )


# ── DiGraph construction ──────────────────────────────────────────────────────


def test_build_graph_returns_digraph(tmp_path):
    nodes = [_make_node("a"), _make_node("b")]
    edges = [_make_edge("a", "b")]
    g = build_graph("s1", nodes, edges, db_url=f"sqlite:///{tmp_path}/test.db")
    import networkx as nx

    assert isinstance(g, nx.DiGraph)
    assert "a" in g.nodes
    assert "b" in g.nodes
    assert g.has_edge("a", "b")


def test_build_graph_empty(tmp_path):
    g = build_graph("s2", [], [], db_url=f"sqlite:///{tmp_path}/test.db")
    assert len(g.nodes) == 0
    assert len(g.edges) == 0


def test_build_graph_single_node_no_edges(tmp_path):
    nodes = [_make_node("only")]
    g = build_graph("s3", nodes, [], db_url=f"sqlite:///{tmp_path}/test.db")
    assert "only" in g.nodes
    assert len(list(g.edges)) == 0


# ── key_module annotation ─────────────────────────────────────────────────────


def test_key_module_top5_marked(tmp_path):
    """Hub node connected to many others should be flagged key_module."""
    hub = _make_node("hub")
    spokes = [_make_node(f"spoke{i}") for i in range(8)]
    nodes = [hub] + spokes
    # hub imports all spokes → highest degree
    edges = [_make_edge("hub", s.node_id) for s in spokes]

    build_graph("s4", nodes, edges, db_url=f"sqlite:///{tmp_path}/test.db")

    key_nodes = [n for n in nodes if n.key_module]
    assert len(key_nodes) <= 5
    assert hub.key_module is True


def test_key_module_fewer_than_5_nodes(tmp_path):
    """When fewer than 5 nodes, all should be key_module."""
    nodes = [_make_node(f"n{i}") for i in range(3)]
    edges = [_make_edge("n0", "n1"), _make_edge("n1", "n2")]
    build_graph("s5", nodes, edges, db_url=f"sqlite:///{tmp_path}/test.db")
    key_count = sum(1 for n in nodes if n.key_module)
    assert key_count <= 3


def test_key_module_exactly_5_or_fewer(tmp_path):
    nodes = [_make_node(f"x{i}") for i in range(10)]
    edges = [_make_edge(f"x{i}", f"x{i+1}") for i in range(9)]
    build_graph("s6", nodes, edges, db_url=f"sqlite:///{tmp_path}/test.db")
    key_count = sum(1 for n in nodes if n.key_module)
    assert key_count <= 5


# ── Persistence ───────────────────────────────────────────────────────────────


def test_nodes_persisted(tmp_path):
    from app.db import evidence_store

    db = f"sqlite:///{tmp_path}/persist.db"
    nodes = [_make_node("p1"), _make_node("p2")]
    edges = [_make_edge("p1", "p2")]
    build_graph("sess_persist", nodes, edges, db_url=db)

    saved = evidence_store.get_nodes("sess_persist", db_url=db)
    assert len(saved) == 2
    ids = {r["node_id"] for r in saved}
    assert ids == {"p1", "p2"}


def test_edges_persisted(tmp_path):
    from app.db import evidence_store

    db = f"sqlite:///{tmp_path}/edgepersist.db"
    nodes = [_make_node("e1"), _make_node("e2")]
    edges = [_make_edge("e1", "e2")]
    build_graph("sess_ep", nodes, edges, db_url=db)

    saved = evidence_store.get_edges("sess_ep", db_url=db)
    assert len(saved) == 1
    assert saved[0]["source_id"] == "e1"
    assert saved[0]["target_id"] == "e2"
    assert saved[0]["evidence_status"] == "confirmed_static"
