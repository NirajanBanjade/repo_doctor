# Feature 01 — Repository X-Ray

## Purpose

Provide a new developer with an interactive, source-linked map of the repository's architecture immediately after import. The map must show modules, their relationships, and the key entry points of the codebase, each backed by concrete file and line references.

---

## Functional Requirements

1. Accept a repository path (local clone or URL).
2. Detect the primary technology stack (language, framework, test runner).
3. Run the language adapter(s) for the detected stack to produce a unified node/edge graph.
4. Invoke the Architecture Agent and Documentation Agent in parallel via Bob to annotate nodes with natural-language summaries and identify documentation quality issues.
5. Return a graph response containing all nodes, edges, evidence status, and agent summaries.
6. Store all findings in the session's SQLite evidence store.
7. The frontend renders the graph using React Flow with clickable nodes that open an evidence panel showing file path, line range, and relationship type.

---

## Inputs

| Input | Source | Format |
|---|---|---|
| `repo_path` | Session creation request | Absolute path on host (trusted sample repo only) |
| `session_id` | Created by session API | UUID |

---

## Outputs

| Output | Destination | Format |
|---|---|---|
| `GraphNode[]` | SQLite `graph_nodes`, REST response | See `docs/api/contracts.md#GraphNode` |
| `GraphEdge[]` | SQLite `graph_edges`, REST response | See `docs/api/contracts.md#GraphEdge` |
| `ArchitectureFindings` | SQLite `bob_outputs`, REST response | See `docs/api/contracts.md#ArchitectureFindings` |
| `DocumentationFindings` | SQLite `bob_outputs`, REST response | See `docs/api/contracts.md#DocumentationFindings` |
| Stack detection result | SQLite `sessions.stack`, REST response | JSON object: `{ language, framework, test_runner }` |

---

## Technical Implementation

### Stack detection (`app/services/repo_importer.py`)

Check for language-specific marker files in priority order:

- `pyproject.toml`, `setup.py`, `requirements.txt` → Python
- `package.json` → Node.js / TypeScript
- Neither → `language = "unknown"`, log warning

For framework detection, scan the Python entry point for FastAPI/Flask/Django imports.

### Adapter dispatch (`app/analysis/adapter_registry.py`)

- Look up adapter by detected language.
- If no adapter matches, return an empty graph with a `no_adapter` warning node.
- Python adapter: traverse all `.py` files, parse with `ast.parse`, extract function defs, class defs, and import statements. Emit `GraphNode` and `GraphEdge` records.

### Graph builder (`app/analysis/graph_builder.py`)

- Receive adapter output; build a `networkx.DiGraph`.
- Persist nodes and edges to SQLite.
- Compute degree centrality; annotate the top-5 highest-degree nodes as `key_module = true`.

### Bob agent invocation (`app/bob/integration.py`)

- Launch Architecture Agent with: node list (name, path, line range), stack info, repo README excerpt.
- Launch Documentation Agent with: README, CONTRIBUTING, setup docs content.
- Await both with `asyncio.gather`.
- Validate responses against `ArchitectureFindings` and `DocumentationFindings` Pydantic schemas.

---

## Dependencies on Other Features

| Feature | Dependency type |
|---|---|
| Session Management | Required — session must exist before X-Ray runs |
| Language Adapters (`base_adapter.py`, `python_adapter.py`) | Required — X-Ray result depends on adapter output |
| Bob Integration module | Required for agent annotations; degrades gracefully if unavailable |
| SQLite Evidence Store | Required — all output must be persisted |

---

## Acceptance Criteria

1. Given the sample repository, X-Ray detects Python + FastAPI and returns at least the module graph for all `.py` files.
2. Every returned edge has `evidence_status`, `file`, and `line` populated.
3. The Architecture Agent summary is displayed per module node in the frontend.
4. Nodes with unknown relationships (dynamic calls) are present in the graph with `evidence_status = "inferred"` — they are not omitted.
5. The Documentation Agent identifies at least one documentation quality issue in the seeded sample repository.
6. If the Python adapter fails on a single file (syntax error), it logs the error, skips the file, and continues — it does not abort the entire X-Ray run.
7. X-Ray completes within 30 seconds for a repository of ≤ 5,000 lines of Python.

---

## Testing Requirements

- Unit test: Python adapter correctly extracts nodes and edges from a known fixture `.py` file.
- Unit test: Graph builder emits correct NetworkX DiGraph from a fixture node/edge list.
- Unit test: Bob output schema validation rejects a malformed `ArchitectureFindings` response.
- Integration test: `POST /api/v1/sessions/{id}/xray` returns 200 with a valid graph for the sample repo fixture.
- Integration test: When no adapter is available for a language, the endpoint returns 200 with an empty graph and a `no_adapter` warning.
