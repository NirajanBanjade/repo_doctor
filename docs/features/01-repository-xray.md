# Feature 01 — Repository X-Ray (Current Implementation)

## Purpose

Create the persisted architecture graph used by every downstream workflow. X-Ray
supports a user-supplied feature wiki as the authoritative source and static
language adapters as the fallback.

## Implemented Flow

1. `POST /api/v1/sessions` validates `repo_path` and optional `architecture_path`.
2. `POST /api/v1/sessions/{id}/xray` detects language, framework, and test runner.
3. With a wiki, `feature_wiki.py` parses one feature per non-README Markdown page.
   Backtick paths create file nodes, arrow flows create edges, and feature links
   create connections. Missing files/titles become warnings.
4. Without a wiki, the registry chooses Python first, then JavaScript/TypeScript.
5. Nodes and edges are stored in SQLite. The Architecture and Documentation Agent
   wrappers run concurrently; because Bob is unwired, attempts are stored as failed
   parses and static results remain available.
6. `GET /api/v1/sessions/{id}/xray/graph` returns nodes, edges, serialized features,
   warnings, and currently-null agent findings.

## Evidence

- Source-extracted and explicitly documented wiki flows are `confirmed_static`.
- A wiki-derived frontend/backend boundary, unresolved imports, and external package
  imports are `inferred`.
- Every returned edge contains `file`, `line`, and `evidence_status`.

## Current Limitations

- Wiki and adapter results are alternatives, not merged layers.
- JS/TS parsing is regex-based and only import relationships are extracted.
- Bob findings are not available until `_call_bob` is implemented.
- Re-running X-Ray does not currently clear older graph rows before inserting.

## Tests

Coverage exists for repository detection, Python and JS/TS adapters, graph building,
wiki parsing, X-Ray routes, unavailable Bob output persistence, and validation/error
paths.
