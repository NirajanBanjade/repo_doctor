"""
app/analysis/impact_engine.py

BFS traversal over the dependency graph to compute impact radius.
See ARCHITECTURE.md §7, docs/features/04-impactscope.md.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field

import networkx as nx


@dataclass
class ImpactRunResult:
    origin_ids: list[str]
    depth: int
    # node_id → depth_level (0 = origin)
    visited: dict[str, int] = field(default_factory=dict)
    # traversed edge tuples (source_id, target_id)
    traversed_edges: list[tuple[str, str]] = field(default_factory=list)


def compute_impact(
    graph: nx.DiGraph,
    origin_ids: list[str],
    depth: int,
) -> ImpactRunResult:
    """
    BFS from origin_ids following PREDECESSORS (callers of the changed node).

    Edge direction: A → B means "A calls/depends on B".
    To find who is affected by changing B, we follow predecessors of B
    (nodes that have an edge pointing to B).

    Returns ImpactRunResult with all reachable nodes and the traversed edges.
    """
    visited: dict[str, int] = {}
    traversed: list[tuple[str, str]] = []
    queue: deque[tuple[str, int]] = deque()

    for nid in origin_ids:
        if nid in graph:
            queue.append((nid, 0))

    while queue:
        node_id, d = queue.popleft()
        if node_id in visited:
            continue
        if d > depth:
            continue
        visited[node_id] = d
        if d < depth:
            for predecessor in graph.predecessors(node_id):
                if predecessor not in visited:
                    traversed.append((predecessor, node_id))
                    queue.append((predecessor, d + 1))

    return ImpactRunResult(
        origin_ids=origin_ids,
        depth=depth,
        visited=visited,
        traversed_edges=traversed,
    )


# ── Git diff parsing ───────────────────────────────────────────────────────────

_HUNK_RE = re.compile(r"^@@.*@@\s*(.*)$")
_DEF_RE = re.compile(r"^\+?\s*(?:def|class)\s+(\w+)")


def parse_diff_symbols(git_diff: str) -> list[str]:
    """
    Extract added/changed function and class names from a unified diff.
    Returns a list of symbol names (may have duplicates; caller deduplicates).
    """
    symbols: list[str] = []
    for line in git_diff.splitlines():
        m = _HUNK_RE.match(line)
        if m:
            rest = m.group(1).strip()
            dm = _DEF_RE.match(rest)
            if dm:
                symbols.append(dm.group(1))
            continue
        dm = _DEF_RE.match(line)
        if dm:
            symbols.append(dm.group(1))
    return symbols
