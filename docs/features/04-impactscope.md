# Feature 04 — ImpactScope (Current Implementation)

## Purpose

Show a bounded set of components that depend on a selected symbol, feature, file, or
diff-derived symbol and preserve the distinction between confirmed relationships and
inferred hypotheses.

## Request

`POST /api/v1/sessions/{id}/impact` requires exactly one origin:

- `symbol_id` — an existing graph node ID;
- `feature_id` — all files owned by a parsed wiki feature;
- `file_path` — converted to `file:{path}`;
- `git_diff` — parsed for hunk symbols and matched by graph-node name.

`depth` must be 1, 2, or 3. `change_description` is optional.

## Implemented Analysis

NetworkX BFS follows predecessors because an edge `A → B` means A depends on B. The
origin has depth zero. The response contains impacted nodes, every stored edge whose
two endpoints are impacted, unresolved symbols, bounded-analysis warnings, optional
Bob annotations, and primary/connected feature information.

The Impact Agent wrapper receives the BFS evidence, but currently returns no
annotations because Bob is unwired. Static impact results are persisted and the
session becomes `impact_complete`.

`GET /api/v1/sessions/{id}/impact/graph` reconstructs the latest persisted result.

## Current Limitations

- Diff parsing is heuristic and name-based.
- Feature connections produce suggestions; they are not automatically added to the
  selected BFS radius.
- `observed_test` promotion is not implemented.

## Tests

Tests cover BFS depth/direction, diff parsing, origin validation, ownership checks,
wiki feature/file origins, result persistence, unresolved inputs, and Bob fallback.
