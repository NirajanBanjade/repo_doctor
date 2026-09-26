"""
tests/test_impact_engine.py

Unit tests for:
- BFS engine (compute_impact)
- Git diff parser (parse_diff_symbols)
- ImpactAnnotations schema validation
"""

from __future__ import annotations

import networkx as nx
import pytest
from pydantic import ValidationError

from app.analysis.impact_engine import compute_impact, parse_diff_symbols
from app.bob.schemas.impact_annotations import ImpactAnnotation, ImpactAnnotations

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_graph(edges: list[tuple[str, str]]) -> nx.DiGraph:
    """Build a DiGraph from (source, target) pairs.  A→B = A calls B."""
    g = nx.DiGraph()
    for src, tgt in edges:
        g.add_edge(src, tgt)
    return g


# ── BFS: depth=1 ──────────────────────────────────────────────────────────────


def test_bfs_depth1_returns_direct_callers():
    # A calls X, B calls X  → changing X affects A and B at depth=1
    g = _make_graph([("A", "X"), ("B", "X")])
    result = compute_impact(g, ["X"], depth=1)
    assert result.visited["X"] == 0
    assert result.visited["A"] == 1
    assert result.visited["B"] == 1


def test_bfs_depth1_does_not_return_depth2_callers():
    # C→A→X: at depth=1 from X, only A is reachable; C is at depth=2
    g = _make_graph([("A", "X"), ("C", "A")])
    result = compute_impact(g, ["X"], depth=1)
    assert "X" in result.visited
    assert "A" in result.visited
    assert "C" not in result.visited


def test_bfs_depth2_returns_transitive_callers():
    g = _make_graph([("A", "X"), ("C", "A")])
    result = compute_impact(g, ["X"], depth=2)
    assert result.visited["X"] == 0
    assert result.visited["A"] == 1
    assert result.visited["C"] == 2


def test_bfs_depth3_three_hops():
    g = _make_graph([("A", "X"), ("B", "A"), ("C", "B")])
    result = compute_impact(g, ["X"], depth=3)
    assert result.visited["C"] == 3


def test_bfs_depth3_stops_at_three():
    # D is 4 hops away — should NOT be included
    g = _make_graph([("A", "X"), ("B", "A"), ("C", "B"), ("D", "C")])
    result = compute_impact(g, ["X"], depth=3)
    assert "D" not in result.visited


# ── BFS: multiple origins ──────────────────────────────────────────────────────


def test_bfs_multiple_origins():
    g = _make_graph([("A", "X"), ("B", "Y")])
    result = compute_impact(g, ["X", "Y"], depth=1)
    assert "X" in result.visited
    assert "Y" in result.visited
    assert "A" in result.visited
    assert "B" in result.visited


# ── BFS: origin not in graph ──────────────────────────────────────────────────


def test_bfs_origin_not_in_graph():
    g = _make_graph([("A", "B")])
    result = compute_impact(g, ["nonexistent"], depth=1)
    assert result.visited == {}


# ── BFS: traversed edges ──────────────────────────────────────────────────────


def test_bfs_traversed_edges_captured():
    g = _make_graph([("A", "X"), ("B", "X")])
    result = compute_impact(g, ["X"], depth=1)
    # traversed_edges are (predecessor, node_id) pairs
    assert ("A", "X") in result.traversed_edges
    assert ("B", "X") in result.traversed_edges


def test_bfs_traversed_edges_empty_for_no_predecessors():
    g = _make_graph([("X", "Y")])
    result = compute_impact(g, ["X"], depth=1)
    assert result.traversed_edges == []


# ── BFS: disconnected node ────────────────────────────────────────────────────


def test_bfs_isolated_origin_only_origin_in_result():
    g = nx.DiGraph()
    g.add_node("X")
    result = compute_impact(g, ["X"], depth=2)
    assert list(result.visited.keys()) == ["X"]


# ── Git diff parser ────────────────────────────────────────────────────────────


def test_parse_diff_symbols_extracts_def():
    diff = """\
--- a/payment.py
+++ b/payment.py
@@ -10,6 +10,7 @@ def process_payment(amount):
+def charge_card(card_id, amount):
+    pass
"""
    symbols = parse_diff_symbols(diff)
    assert "charge_card" in symbols


def test_parse_diff_symbols_extracts_class():
    diff = """\
--- a/models.py
+++ b/models.py
@@ -1,3 +1,4 @@
+class Order:
+    pass
"""
    symbols = parse_diff_symbols(diff)
    assert "Order" in symbols


def test_parse_diff_symbols_hunk_header_def():
    diff = """\
--- a/orders.py
+++ b/orders.py
@@ -5,3 +5,4 @@ def process_order(order_id):
     return order
"""
    symbols = parse_diff_symbols(diff)
    assert "process_order" in symbols


def test_parse_diff_symbols_empty_diff():
    assert parse_diff_symbols("") == []


def test_parse_diff_symbols_no_python_symbols():
    diff = '--- a/data.json\n+++ b/data.json\n@@ -1 +1 @@\n-{}\n+{"x": 1}\n'
    assert parse_diff_symbols(diff) == []


# ── ImpactAnnotations schema ──────────────────────────────────────────────────


def test_impact_annotations_valid():
    data = {
        "annotations": [
            {"node_id": "n1", "risk": "may break", "hypothesis_label": "hypothesis"},
        ],
        "analysis_notes": ["check carefully"],
    }
    result = ImpactAnnotations.model_validate(data)
    assert len(result.annotations) == 1
    assert result.annotations[0].evidence_status == "inferred"


def test_impact_annotation_missing_node_id_raises():
    with pytest.raises(ValidationError):
        ImpactAnnotation.model_validate({"risk": "some risk"})


def test_impact_annotations_empty_list_valid():
    data = {"annotations": [], "analysis_notes": []}
    result = ImpactAnnotations.model_validate(data)
    assert result.annotations == []


def test_impact_annotation_evidence_status_always_inferred():
    ann = ImpactAnnotation(node_id="x", risk="r")
    assert ann.evidence_status == "inferred"
