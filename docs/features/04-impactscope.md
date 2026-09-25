# Feature 04 — ImpactScope

## Purpose

Given a selected function or Git diff and an optional description of an intended behavior change, show the developer every code component that may be affected up to a configurable hop depth (1–3), with per-edge evidence and clear distinction between statically confirmed relationships, test-observed relationships, and AI-inferred hypotheses.

---

## Functional Requirements

1. Accept a selected symbol ID (from the graph) or a raw Git diff as the change origin.
2. Accept an optional natural-language description of the intended behavior change.
3. Accept an impact depth of 1, 2, or 3 hops.
4. Run BFS over the dependency graph from the origin node, traversing edges in the **dependent direction** (callers of the changed function, then callers of those callers, etc.).
5. Return all reachable nodes within the selected depth, with their depth level.
6. For each edge in the traversal path, include: relationship type, source file, source line, and evidence status.
7. Invoke the Impact Agent via Bob to annotate the BFS result with behavior-specific risk hypotheses derived from the intended change description.
8. Label all Bob-provided hypotheses as `inferred`; they do not override static analysis evidence.
9. Display dynamic or unresolved calls (e.g., `getattr`, callback registrations) as `inferred` edges; do not omit them.
10. Clearly display the selected depth and a note that the analysis is bounded (not exhaustive).
11. Record the impact run (symbol, depth, resulting nodes/edges) in the session evidence store.

---

## Inputs

| Input | Source | Format |
|---|---|---|
| `session_id` | URL parameter | UUID |
| `symbol_id` | Request body | String matching a `graph_nodes.node_id` |
| `git_diff` | Request body (alternative to `symbol_id`) | Raw unified diff text |
| `change_description` | Request body (optional) | Free-form string |
| `depth` | Request body | Integer 1–3 |

Exactly one of `symbol_id` or `git_diff` must be provided. If both are provided, return `400 Bad Request`.

If `git_diff` is provided, the backend must identify which `graph_nodes` correspond to changed symbols before running BFS.

---

## Outputs

| Output | Destination | Format |
|---|---|---|
| `ImpactRunResult` | SQLite `impact_results`, `impact_nodes`, REST response | See `docs/api/contracts.md#ImpactRunResult` |
| `ImpactAnnotations` | SQLite `bob_outputs`, REST response | See `docs/api/contracts.md#ImpactAnnotations` |
| Per-edge evidence records | SQLite `graph_edges` (evidence_status updated) | — |

---

## Technical Implementation

### BFS traversal (`app/analysis/impact_engine.py`)

```python
def compute_impact(
    graph: nx.DiGraph,
    origin_ids: list[str],
    depth: int,
) -> ImpactRunResult:
    # BFS from origin(s), following INCOMING edges (dependents)
    # graph edge direction: source → target means "source calls target"
    # BFS must follow PREDECESSORS of origin (who calls origin?)
    visited = {}  # node_id → depth_level
    queue = deque([(node_id, 0) for node_id in origin_ids])
    while queue:
        node_id, d = queue.popleft()
        if node_id in visited or d > depth:
            continue
        visited[node_id] = d
        for predecessor in graph.predecessors(node_id):
            queue.append((predecessor, d + 1))
    return ImpactRunResult(nodes=visited, origin=origin_ids, depth=depth)
```

**Graph edge convention:** An edge `A → B` means "A depends on B" (A calls/imports B). To find dependents of a changed node `X`, traverse predecessors (nodes that have an edge pointing to `X`).

### Git diff parsing

When `git_diff` is provided:
1. Parse the diff to extract changed file paths and function names using a regex on `@@` hunks and `def ` / `class ` markers.
2. Look up matching `graph_nodes` by path + name.
3. If no match is found for a changed symbol, log it as `unresolved_symbol` — do not fail the request.

### Impact Agent invocation

Pass Bob: origin node details, BFS result (node names, paths, relationships), and `change_description`.
Validate response against `ImpactAnnotations` schema: list of `{ node_id, risk, hypothesis_label }`.

All hypotheses have `evidence_status = "inferred"` in the response; they do not modify the graph edges in SQLite.

---

## Dependencies on Other Features

| Feature | Dependency type |
|---|---|
| Session Management | Required |
| Repository X-Ray | Required — the dependency graph must exist |
| Bob Integration | Soft — degrades to unannotated BFS result if unavailable |
| SQLite Evidence Store | Required |

---

## Acceptance Criteria

1. BFS correctly identifies direct callers (depth 1) and transitive callers (depth 2–3) of a changed function in the sample repository.
2. Each edge in the result has `evidence_status`, `file`, and `line` populated.
3. Dynamic/inferred edges are present in the graph with `evidence_status = "inferred"` — they are never omitted.
4. The selected depth and a "bounded analysis" disclaimer are visible in the frontend.
5. The Impact Agent's hypotheses are labeled distinctly from confirmed edges in the UI.
6. A Git diff input correctly resolves to at least one graph node for any diff touching a known `.py` file in the sample repo.
7. An unresolvable diff symbol does not cause a 500 error — it appears as a `unresolved_symbol` warning in the response.
8. The seeded downstream regression (changed payment function affecting order-processing caller) is identified at depth ≤ 2.

---

## Testing Requirements

- Unit test: BFS engine returns correct node set and depth levels for a known fixture graph.
- Unit test: BFS with `depth=1` does not return depth-2 nodes.
- Unit test: Git diff parser correctly extracts function names from a known diff fixture.
- Unit test: `ImpactAnnotations` schema validation rejects a hypothesis missing `node_id`.
- Integration test: `POST /api/v1/sessions/{id}/impact` returns a valid `ImpactRunResult` for a known symbol.
- Integration test: Providing both `symbol_id` and `git_diff` returns 400.
- Integration test: Seeded regression node appears in the result at the correct depth.
