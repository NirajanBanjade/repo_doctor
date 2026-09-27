# RepoDoc — Current System Architecture

## 1. Runtime Shape

```text
React/TypeScript UI
        | /api/v1 REST
        v
FastAPI workflow service ---- SQLite evidence store
        |
        +---- adapters / feature-wiki parser / NetworkX
        +---- Docker setup and pytest runners
        +---- Bob boundary (transport currently stubbed)
```

The backend owns sessions, graph data, evidence, approvals, generated-file metadata,
test results, and verification reports. The browser never calls Bob or Docker. Bob
outputs must enter through `app/bob/integration.py` and pass Pydantic validation.

## 2. Implemented Workflow

### Session and architecture source

`POST /api/v1/sessions` accepts a local `repo_path` and optional
`architecture_path`. Both are resolved and validated. A supplied wiki must contain at
least one non-README Markdown page. Its path is retained in the session's `stack`
JSON when later stack detection enriches that object.

### X-Ray

`POST /api/v1/sessions/{id}/xray` selects one architecture source:

1. With `architecture_path`, `feature_wiki.py` builds the authoritative file-level
   feature graph.
2. Otherwise, the registry selects the Python or JavaScript/TypeScript adapter.

Nodes and edges are persisted. Architecture and Documentation Agent wrappers run
concurrently, but Bob currently returns `None`; attempts are still saved with
`parsed_ok=false`.

### ImpactScope

An impact request accepts exactly one of `symbol_id`, `feature_id`, `file_path`, or
`git_diff`, plus depth 1–3. Features expand to their owned files, file paths become
`file:{path}`, and diffs use deterministic symbol extraction. BFS follows graph
predecessors because `A → B` means A depends on B. Results include all relationships
within the impacted set and optional connected-feature suggestions.

### Test planning and execution

```text
impact run -> select nodes -> map pytest files
           -> Bob Test Agent or deterministic fallback
           -> proposed/refined plan -> approve or reject
           -> approval writes working-copy files
           -> explicit run action -> persisted results
```

The fallback planner derives normal-path, branch, exception, and FastAPI route
scenarios from Python AST evidence. Unsupported/file-level nodes receive a source
contract. Generated tests are conservative source checks and are not equivalent to
complete behavioral coverage.

Docker mounts the repository at `/repo:ro` and working copy at `/working_copy:ro`,
uses one CPU and 512 MB, disables networking, and times out after 120 seconds. Pytest
JSON results and infrastructure state are persisted.

### Verification

`GET /api/v1/sessions/{id}/verification` is create-or-read. It returns a cached
report or aggregates the latest impact, plan, tests, environment checks, inferred
nodes, and wiki scope. It attempts the Verification Agent, falls back deterministically,
and may write documentation patches into the working copy.

## 3. Backend Modules

| Responsibility | Module |
|---|---|
| Sessions | `app/services/session.py`, `app/api/routes/sessions.py` |
| Stack detection | `app/services/repo_importer.py` |
| Feature wiki | `app/services/feature_wiki.py` |
| Static analysis | `app/analysis/adapters/` |
| Graph and impact | `app/analysis/graph_builder.py`, `app/analysis/impact_engine.py` |
| Environment Doctor | `app/services/environment_doctor.py`, `app/sandbox/docker_runner.py` |
| Test mapping/planning | `app/services/test_mapper.py`, `app/services/deterministic_test_planner.py` |
| Test generation/execution | `app/services/test_generator.py`, `app/sandbox/test_executor.py` |
| Verification | `app/services/verification.py` |
| Bob boundary | `app/bob/integration.py`, `app/bob/schemas/` |
| Persistence | `app/db/models.py`, `app/db/evidence_store.py` |

## 4. Feature-Wiki Model

Each non-README page is a feature. The parser recognizes a `#` title, `## Frontend`
and `## Backend`, backtick paths, arrow-separated flows, and links to other feature
pages. Documented flows are `confirmed_static`; a synthesized frontend/backend
boundary is `inferred`. Missing titles and files produce warnings.

## 5. Adapter Model

`AdapterBase` provides deterministic `detect`, `extract_nodes`, and `extract_edges`.
Python wins in mixed repositories because it appears first in the registry.

- Python uses `ast` for module, class, function, import, call, and inheritance data.
- JavaScript/TypeScript scans common JS/TS extensions with deterministic regexes,
  emits file/class/function nodes and import edges, and labels external or unresolved
  imports `inferred`.

The TypeScript adapter does not use the compiler API.

## 6. Evidence Rules

| Status | Rule |
|---|---|
| `confirmed_static` | Extracted from source, or explicitly documented in the designated authoritative wiki. Includes `file` and `line`. |
| `inferred` | Relationship or hypothesis without confirmed source resolution. |
| `observed_test` | Reserved for a future runtime trace; current tests do not promote edges. |

## 7. Bob Boundary

Wrappers exist for Architecture, Documentation, Environment, Impact, Test, and
Verification Agents. There is no Contribution Agent wrapper. `_call_bob` is an
unwired stub, so callers must retain deterministic/empty fallbacks. Raw unavailable
or invalid responses are persisted with `parsed_ok=false`.

## 8. Implemented REST API

All routes have prefix `/api/v1/sessions`:

```text
POST /                                      create session
GET  /{id}                                  get session
POST /{id}/xray                             run X-Ray (202)
GET  /{id}/xray/graph                       get graph
POST /{id}/environment/run                  run setup (202)
POST /{id}/environment/fix                  apply approved patch/rerun (202)
GET  /{id}/environment/checks               get check history
GET  /{id}/environment/status               get latest environment run
POST /{id}/impact                           run impact (202)
GET  /{id}/impact/graph                     get latest impact
POST /{id}/tests/plan                       create/get plan (202)
GET  /{id}/tests/plan                       get latest plan
POST /{id}/tests/plan/{plan}/refine         refine proposed plan
POST /{id}/tests/plan/{plan}/approve        approve/reject and generate
POST /{id}/tests/plan/{plan}/run            run approved plan (202)
GET  /{id}/tests/plan/{plan}/result         get plan result
GET  /{id}/tests/results                    get latest result
GET  /{id}/verification                     create/get verification
```

No FirstPR or WebSocket route is registered.

## 9. Persistence

SQLAlchemy Core defines `sessions`, `graph_nodes`, `graph_edges`, `bob_outputs`,
`environment_checks`, `impact_results`, `impact_nodes`, `test_plans`, `test_results`,
and `verification_reports`. Generated paths/status live in scenario JSON after
approval. Each execution row stores stdout, stderr, exit code, infrastructure state,
per-test JSON, and component-status JSON.

The SQLite engine is a lazy module singleton and tests reset it between cases. There
are no formal Alembic migrations; a compatibility upgrade adds newer plan columns.

## 10. Frontend

The UI exposes Import, X-Ray, Environment Doctor, ImpactScope, Test Plan, Test
Results, and Verification. FirstPR code remains but its tab is hidden because its
backend is absent. React Query owns server state, Axios is the API client, and React
Flow renders graphs.

## 11. Open Decisions

1. Select and implement the Bob transport.
2. Add runtime trace correlation before using `observed_test`.
3. Replace compatibility upgrades with Alembic migrations.
4. Implement FirstPR end to end or remove dormant code.
5. Add real-time events only if streaming remains required.
6. Separate PR-summary creation from approval if pre-creation approval remains a
   product requirement.
7. Decide whether wiki and adapter graphs should eventually be merged.
