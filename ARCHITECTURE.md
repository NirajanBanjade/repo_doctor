# RepoDoc — System Architecture

## 1. Overview

RepoDoc is a developer-onboarding tool that transforms an unfamiliar repository into a guided, evidence-backed contribution path. It is composed of three major runtime layers:

```
┌──────────────────────────────────────────────────────────────────┐
│                        React Frontend                            │
│         (Architecture map, impact graph, approvals, reports)     │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP/REST + WebSocket (status events)
┌───────────────────────────▼──────────────────────────────────────┐
│                   FastAPI Workflow Service                        │
│   (Session management, feature orchestration, evidence store)    │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐  │
│  │ Repo Parser    │  │ Impact Graph   │  │ Sandbox Runner     │  │
│  │ (language      │  │ Builder        │  │ (Docker, pytest)   │  │
│  │  adapters)     │  │ (NetworkX)     │  │                    │  │
│  └────────────────┘  └────────────────┘  └────────────────────┘  │
│                                                                  │
│                SQLite Evidence & Session Store                   │
└───────────────────────────┬──────────────────────────────────────┘
                            │ Bob integration interface
┌───────────────────────────▼──────────────────────────────────────┐
│                     IBM Bob 2.0 Agent Layer                      │
│  (Architecture Agent, Documentation Agent, Impact Agent,         │
│   Environment Agent, Contribution Agent, Verification Agent)     │
└──────────────────────────────────────────────────────────────────┘
```

The three layers are strictly separated:
- The **frontend** renders data and captures developer decisions; it never calls Bob directly.
- The **backend** owns all business logic, persists all evidence, and is the sole consumer of Bob structured outputs.
- **Bob agents** perform investigation and analysis; they do not write to the database directly.

---

## 2. Backend Responsibilities (FastAPI)

| Responsibility | Module |
|---|---|
| Session lifecycle, feature state machine | `app/services/session.py` |
| Repository import, stack detection | `app/services/repo_importer.py` |
| Language adapter dispatch | `app/analysis/adapter_registry.py` |
| Unified dependency graph construction | `app/analysis/graph_builder.py` |
| Impact radius traversal (BFS, depth 1–3) | `app/analysis/impact_engine.py` |
| Environment setup orchestration | `app/services/environment_doctor.py` |
| Sandbox container lifecycle | `app/sandbox/docker_runner.py` |
| Test discovery and mapping | `app/services/test_mapper.py` |
| Test generation coordination | `app/services/test_generator.py` |
| Test execution in sandbox | `app/sandbox/test_executor.py` |
| Evidence persistence | `app/db/evidence_store.py` |
| Bob integration (structured output consumer) | `app/bob/integration.py` |
| REST API layer | `app/api/routes/` |

---

## 3. Frontend Responsibilities (React + TypeScript)

| Responsibility | Component |
|---|---|
| Repository import and stack display | `ImportView` |
| Architecture map (React Flow, evidence links) | `ArchitectureMapView` |
| Environment Doctor status and blockers | `EnvironmentDoctorView` |
| FirstPR task picker and learning path | `FirstPRView` |
| Impact graph renderer and depth selector | `ImpactGraphView` |
| Test plan review and approval UI | `TestPlanView` |
| Test results and per-component status | `TestResultsView` |
| Verification report and PR summary | `VerificationView` |
| Shared evidence panel (file:line navigation) | `EvidencePanel` |
| Approval gate modal (generated files/tests) | `ApprovalModal` |

The frontend is a pure consumer of the REST API. It does not perform analysis, call Bob, or mutate the repository.

---

## 4. Language-Adapter Architecture

The repository parser is language-agnostic at the orchestration level. Each language adapter implements a shared interface and emits a normalized node/edge graph.

```
app/analysis/
├── adapter_registry.py        # maps detected language → adapter class
├── base_adapter.py            # abstract interface: AdapterBase
├── adapters/
│   ├── python_adapter.py      # Python AST (stdlib `ast`) + importlib
│   └── typescript_adapter.py  # TypeScript Compiler API (future)
└── graph_builder.py           # merges adapter output into NetworkX DiGraph
```

### AdapterBase interface

```python
class AdapterBase:
    def detect(self, repo_path: str) -> bool: ...
    def extract_nodes(self, repo_path: str) -> list[GraphNode]: ...
    def extract_edges(self, repo_path: str) -> list[GraphEdge]: ...
```

### GraphNode (language-neutral)

```
id: str               # "module::function" canonical key
kind: str             # "function" | "class" | "module" | "file"
name: str
path: str             # relative to repo root
line_start: int
line_end: int
language: str
summary: str | None   # populated by Architecture Agent
```

### GraphEdge (language-neutral)

```
source_id: str
target_id: str
relationship: str     # "calls" | "imports" | "inherits" | "uses"
file: str
line: int
evidence_status: str  # "confirmed_static" | "observed_test" | "inferred"
```

**MVP scope:** Python adapter only. The TypeScript adapter stub is registered but returns an empty graph with a clear warning.

---

## 5. Unified Dependency Graph and Evidence Model

The backend maintains a **single NetworkX DiGraph** per analysis session. It is the source of truth for both Repository X-Ray and ImpactScope.

```
session → DiGraph (nodes: GraphNode, edges: GraphEdge)
        → persisted as edge-list in SQLite (graph_edges table)
        → queried by impact_engine.py for BFS traversal
        → enriched by evidence records after test execution
```

### Evidence status rules

| Status | Meaning | When set |
|---|---|---|
| `confirmed_static` | Edge found by static AST/TS analysis | After adapter extraction |
| `observed_test` | Edge traversed by an executed test (instrumented) | After sandbox test run with coverage |
| `inferred` | Suggested by Bob agent reasoning, no code proof | When Bob proposes an edge without AST confirmation |

An edge must never be promoted from `inferred` to `confirmed_static` without re-running the relevant adapter on the source file.

---

## 6. IBM Bob Agent Responsibilities and Integration Boundaries

Bob agents are invoked by the backend via the supported Bob integration interface. They return structured outputs (JSON objects matching defined schemas in `docs/api/contracts.md`). The backend consumes these outputs, validates them, and persists them to SQLite.

**Bob must not:**
- Write directly to the database.
- Execute commands on the host outside the sandbox.
- Create or merge branches autonomously.

### Agent roster

| Agent | Role | Trigger | Output schema |
|---|---|---|---|
| **Architecture Agent** | Analyze module structure, entry points, and key relationships | After repo import | `ArchitectureFindings` |
| **Documentation Agent** | Parse README, setup docs, contribution guidelines | After repo import (parallel with Architecture Agent) | `DocumentationFindings` |
| **Environment Agent** | Diagnose setup failures; verify approved fixes | After Docker run fails | `EnvironmentDiagnosis` |
| **Impact Agent** | Explore dependent code paths; annotate BFS graph edges | After impact radius selection | `ImpactAnnotations` |
| **Test Agent** | Map existing tests; identify coverage gaps; propose test scenarios | After impact radius selection (parallel with Impact Agent) | `TestPlanProposal` |
| **Contribution Agent** | Guide the starter task with repo-specific explanation | After FirstPR task selection | `ContributionGuidance` |
| **Verification Agent** | Reconcile test results with acceptance criteria and impact risks | After test execution | `VerificationReport` |

### Integration pattern

```
Backend service
  → bob_integration.invoke(agent="impact_agent", payload=ImpactPayload)
  → Bob executes agent workflow
  → Returns structured JSON
  → backend validates schema
  → backend writes to SQLite, updates session state
  → REST response to frontend
```

If Bob does not expose a direct invocation API, the backend calls Bob through its available agent interface and parses the structured output section of the response. Any Bob output that cannot be validated against the expected schema is stored as raw text and flagged for review — it is never silently accepted as structured data.

---

## 7. API Design and Data Flow

All backend routes are versioned under `/api/v1/`. The frontend communicates exclusively through these routes. Bob outputs enter the system only through the backend's `bob/integration.py` module.

### Primary data flows

```
1. Repository import
   POST /api/v1/sessions          → creates session, triggers import
   GET  /api/v1/sessions/{id}     → session state + stack detection result

2. Architecture X-Ray
   POST /api/v1/sessions/{id}/xray         → runs adapter + Architecture Agent
   GET  /api/v1/sessions/{id}/xray/graph   → returns nodes + edges with evidence

3. Environment Doctor
   POST /api/v1/sessions/{id}/environment/run     → start Docker setup
   GET  /api/v1/sessions/{id}/environment/status  → live check results
   POST /api/v1/sessions/{id}/environment/fix     → apply approved fix, re-run

4. ImpactScope
   POST /api/v1/sessions/{id}/impact        → { symbol | diff, depth }
   GET  /api/v1/sessions/{id}/impact/graph  → BFS result + annotations

5. Test generation
   GET  /api/v1/sessions/{id}/tests/plan    → proposed test plan (before approval)
   POST /api/v1/sessions/{id}/tests/approve → developer approves plan
   POST /api/v1/sessions/{id}/tests/run     → generate + execute in sandbox
   GET  /api/v1/sessions/{id}/tests/results → per-component results

6. Verification
   GET  /api/v1/sessions/{id}/verification  → final report + PR summary
```

WebSocket endpoint `ws/sessions/{id}/events` pushes real-time status events (container logs, agent progress) to the frontend.

---

## 8. Test Generation and Isolated Execution

```
Impact graph
  ↓ (selected nodes)
Test Mapper
  → discovers existing pytest tests linked to affected symbols
  → identifies coverage gaps per selected node
  ↓
Test Agent (Bob)
  → proposes scenario list (test plan) per affected component
  ↓
Developer approval gate
  ↓ (approved)
Test Generator
  → generates .py patch files in working copy (not original repo)
  ↓
Sandbox Runner (Docker)
  → mounts working copy read-only
  → runs: pytest {existing tests} {generated tests} --tb=short
  → captures stdout, stderr, exit code, per-test status
  ↓
Evidence Store
  → saves per-component status: passed / failed / unexecuted / no_test
  → links each generated test back to its graph node(s)
  ↓
Verification Agent (Bob)
  → reconciles results with stated risks
  → outputs VerificationReport
```

Generated test files are placed in a `working_copy/` directory isolated from the original repository clone. The original clone is never modified.

---

## 9. Session and Evidence Storage (SQLite)

```
sessions            id, repo_url, status, stack, created_at
graph_nodes         id, session_id, node_id, kind, name, path, line_start, line_end
graph_edges         id, session_id, source_id, target_id, relationship, file, line, evidence_status
environment_checks  id, session_id, step, command, stdout, stderr, status, verified_at
impact_results      id, session_id, run_id, symbol, depth, created_at
impact_nodes        id, run_id, node_id, depth_level
test_plans          id, session_id, run_id, scenario, component_id, evidence, status
test_results        id, plan_id, test_file, test_name, status, stdout, stderr
verification_reports id, session_id, run_id, summary, pr_summary, risks_unresolved
bob_outputs         id, session_id, agent, raw_output, parsed_ok, created_at
```

---

## 10. Directory Structure

```
repodoc/
├── ARCHITECTURE.md
├── AGENTS.md
├── PRD (1).md
├── docs/
│   ├── features/
│   │   ├── 01-repository-xray.md
│   │   ├── 02-environment-doctor.md
│   │   ├── 03-firstpr.md
│   │   ├── 04-impactscope.md
│   │   ├── 05-radius-test-generator.md
│   │   └── 06-verification-documentation.md
│   └── api/
│       └── contracts.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── sessions.py
│   │   │       ├── xray.py
│   │   │       ├── environment.py
│   │   │       ├── impact.py
│   │   │       ├── tests.py
│   │   │       └── verification.py
│   │   ├── analysis/
│   │   │   ├── adapter_registry.py
│   │   │   ├── base_adapter.py
│   │   │   ├── graph_builder.py
│   │   │   ├── impact_engine.py
│   │   │   └── adapters/
│   │   │       ├── python_adapter.py
│   │   │       └── typescript_adapter.py
│   │   ├── bob/
│   │   │   ├── integration.py
│   │   │   └── schemas/
│   │   │       ├── architecture_findings.py
│   │   │       ├── documentation_findings.py
│   │   │       ├── environment_diagnosis.py
│   │   │       ├── impact_annotations.py
│   │   │       ├── test_plan_proposal.py
│   │   │       ├── contribution_guidance.py
│   │   │       └── verification_report.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   ├── evidence_store.py
│   │   │   └── migrations/
│   │   ├── sandbox/
│   │   │   ├── docker_runner.py
│   │   │   └── test_executor.py
│   │   └── services/
│   │       ├── session.py
│   │       ├── repo_importer.py
│   │       ├── environment_doctor.py
│   │       ├── test_mapper.py
│   │       └── test_generator.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # typed API client (axios)
│   │   ├── components/
│   │   │   ├── ArchitectureMapView/
│   │   │   ├── EnvironmentDoctorView/
│   │   │   ├── FirstPRView/
│   │   │   ├── ImpactGraphView/
│   │   │   ├── TestPlanView/
│   │   │   ├── TestResultsView/
│   │   │   ├── VerificationView/
│   │   │   ├── EvidencePanel/
│   │   │   └── ApprovalModal/
│   │   ├── hooks/        # useSession, useGraph, useImpact …
│   │   ├── types/        # TypeScript interfaces matching API contracts
│   │   └── App.tsx
│   ├── package.json
│   └── tsconfig.json
├── sample_repo/          # the seeded demo FastAPI/PostgreSQL/pytest app
│   ├── app/
│   ├── tests/
│   ├── docker-compose.yml
│   └── README.md
└── docker/
    ├── Dockerfile.backend
    ├── Dockerfile.sandbox
    └── docker-compose.yml
```

---

## 11. Open Questions and Inconsistencies in the PRD

The following points are unresolved in the PRD and must be decided before implementation begins:

| # | Issue | Location in PRD | Decision needed |
|---|---|---|---|
| 1 | The product is called **RepoDoc** in the title but **OnboardIQ** in §3 MVP Architecture. | §3 | Confirm canonical product name. |
| 2 | Bob 2.0 orchestration API is undefined. The PRD says "implement integration using the Bob features actually available in the hackathon environment." No specific invocation endpoint is given. | §6 | Document exactly which Bob interface (CLI, HTTP, SDK) is available and what the structured output format is. |
| 3 | TypeScript adapter is listed in the tech stack but the MVP explicitly says "initially implement Python support." The TypeScript Compiler API requires a Node.js process. | §3, §7 | Confirm TypeScript adapter is stub-only for MVP; define how the Node.js subprocess is spawned from Python if it is in scope. |
| 4 | The sample repository specification (§9) says "2–3 onboarding obstacles, one bounded starter task, one seeded regression." The sample repo is not created or described anywhere. | §9 | Define the sample repo contents, the seeded regression location, and the starter task before implementing the demo flow. |
| 5 | SQLite is specified for storage (§7) but the sample app uses PostgreSQL. It is not clear whether the SQLite instance is the RepoDoc backend store or a test store for the sample app. | §7 | Confirm: SQLite is the RepoDoc evidence store; PostgreSQL is used only inside the sample app container. |
| 6 | "Instrumented test execution" (§5.1) is mentioned as a way to promote edge status to `observed_test`, but no instrumentation mechanism (coverage.py, pytest-cov, tracing hooks) is specified. | §5.1 | Decide whether pytest-cov branch tracing or a custom AST hook is used to produce the edge observation signal. |
| 7 | The WebSocket event format is not defined anywhere in the PRD. | §7 tech stack | Specify event schema for container logs and agent progress. |
| 8 | Approval gate granularity is unclear: is approval per test plan, per generated file, or per individual test case? | §5.2 | Define the minimum approval unit. |
