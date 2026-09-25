# RepoDoc — Shared Data Structures and API Contracts

This document is the single source of truth for all data types shared between the backend, frontend, and Bob agent schemas. TypeScript interfaces in `frontend/src/types/` and Pydantic models in `backend/app/bob/schemas/` and `backend/app/api/` must match these definitions exactly.

Versioning: all REST endpoints are under `/api/v1/`. Breaking changes require a version bump.

---

## Table of Contents

1. [Core Domain Types](#1-core-domain-types)
2. [Session](#2-session)
3. [Repository X-Ray](#3-repository-x-ray)
4. [Environment Doctor](#4-environment-doctor)
5. [ImpactScope](#5-impactscope)
6. [Radius Test Generator](#6-radius-test-generator)
7. [Verification & Documentation](#7-verification--documentation)
8. [Bob Agent Output Schemas](#8-bob-agent-output-schemas)
9. [WebSocket Events](#9-websocket-events)
10. [Error Responses](#10-error-responses)

---

## 1. Core Domain Types

### GraphNode

Represents a named code entity (function, class, module, or file) extracted by a language adapter.

```typescript
interface GraphNode {
  node_id: string;          // canonical key: "relative/path.py::ClassName::method_name"
  kind: "function" | "class" | "module" | "file";
  name: string;             // unqualified name
  path: string;             // path relative to repo root
  line_start: number;
  line_end: number;
  language: string;         // "python" | "typescript" | "unknown"
  summary: string | null;   // populated by Architecture Agent
  key_module: boolean;      // true for top-5 highest-degree nodes
}
```

### GraphEdge

Represents a directed dependency relationship between two `GraphNode` entries.

```typescript
interface GraphEdge {
  edge_id: string;          // UUID
  source_id: string;        // node_id of the dependent (the caller/importer)
  target_id: string;        // node_id of the dependency (the callee/imported)
  relationship: "calls" | "imports" | "inherits" | "uses";
  file: string;             // file where this relationship is expressed
  line: number;             // line number in that file
  evidence_status: "confirmed_static" | "observed_test" | "inferred";
  note: string | null;      // for inferred edges: reason for inference
}
```

**Edge direction convention:** `source_id → target_id` means "`source` depends on `target`" (source calls/imports target). To find what depends on a node, look for edges where `target_id` equals the node.

### EvidenceRef

A pointer to a specific source location used as evidence.

```typescript
interface EvidenceRef {
  file: string;
  line: number;
  snippet: string | null;   // up to 3 lines of context
  evidence_status: "confirmed_static" | "observed_test" | "inferred";
}
```

### StarterTask

Static task definition for FirstPR.

```typescript
interface StarterTask {
  id: string;
  title: string;
  description: string;
  target_symbol: string;          // node_id in the graph
  target_file: string;
  target_line: number;
  recommended_impact_depth: 1 | 2 | 3;
}
```

---

## 2. Session

### Session (response)

```typescript
interface Session {
  session_id: string;         // UUID
  status: SessionStatus;
  repo_path: string;
  stack: StackDetection | null;
  created_at: string;         // ISO 8601
  updated_at: string;
}

type SessionStatus =
  | "created"
  | "importing"
  | "xray_running"
  | "xray_complete"
  | "environment_running"
  | "environment_complete"
  | "impact_running"
  | "impact_complete"
  | "tests_running"
  | "tests_complete"
  | "verified"
  | "error";

interface StackDetection {
  language: string;
  framework: string | null;
  test_runner: string | null;
  adapter_available: boolean;
}
```

### POST /api/v1/sessions — Request

```typescript
interface CreateSessionRequest {
  repo_path: string;    // absolute path to the trusted sample repo on the host
}
```

---

## 3. Repository X-Ray

### XRayResult (GET /api/v1/sessions/{id}/xray/graph)

```typescript
interface XRayResult {
  session_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  architecture_findings: ArchitectureFindings | null;
  documentation_findings: DocumentationFindings | null;
  warnings: string[];   // e.g., ["no_adapter: TypeScript adapter not available"]
}
```

---

## 4. Environment Doctor

### EnvironmentCheck

```typescript
interface EnvironmentCheck {
  check_id: string;     // UUID
  session_id: string;
  step_index: number;
  command: string;
  stdout: string;
  stderr: string;
  exit_code: number;
  status: "verified" | "failed" | "blocked" | "infrastructure_error";
  verified_at: string | null;     // ISO 8601; set only when status = "verified"
}
```

### EnvironmentRunResult (GET /api/v1/sessions/{id}/environment/status)

```typescript
interface EnvironmentRunResult {
  session_id: string;
  run_id: string;
  checks: EnvironmentCheck[];
  all_verified: boolean;
  diagnosis: EnvironmentDiagnosis | null;   // null if no failure
}
```

### POST /api/v1/sessions/{id}/environment/fix — Request

```typescript
interface ApplyFixRequest {
  step_id: string;
  approval: true;           // literal true required — not a boolean field
  patch_content: string | null;   // optional file patch; null = no file change needed
}
```

---

## 5. ImpactScope

### POST /api/v1/sessions/{id}/impact — Request

```typescript
interface ImpactRequest {
  symbol_id?: string;         // exactly one of symbol_id or git_diff
  git_diff?: string;
  change_description?: string;
  depth: 1 | 2 | 3;
}
```

### ImpactRunResult (GET /api/v1/sessions/{id}/impact/graph)

```typescript
interface ImpactRunResult {
  run_id: string;
  session_id: string;
  origin_ids: string[];
  depth: 1 | 2 | 3;
  change_description: string | null;
  nodes: ImpactNode[];
  edges: GraphEdge[];           // subset of graph edges traversed in BFS
  annotations: ImpactAnnotation[];
  unresolved_symbols: string[]; // symbols from git_diff not found in graph
  warnings: string[];
}

interface ImpactNode {
  node_id: string;
  depth_level: number;          // 0 = origin, 1 = direct caller, etc.
  node: GraphNode;
  existing_tests: string[];     // test file paths, if already known
}

interface ImpactAnnotation {
  node_id: string;
  risk: string;                 // human-readable risk description
  hypothesis_label: string;     // always "hypothesis" until validated
  evidence_status: "inferred";  // always inferred for Bob annotations
}
```

---

## 6. Radius Test Generator

### TestPlanProposal (GET /api/v1/sessions/{id}/tests/plan)

```typescript
interface TestPlanProposal {
  plan_id: string;
  session_id: string;
  impact_run_id: string;
  status: "proposed" | "approved" | "rejected";
  scenarios: TestScenario[];
  existing_test_mappings: ExistingTestMapping[];
  coverage_gaps: string[];    // node_ids with no existing test
}

interface TestScenario {
  scenario_id: string;
  name: string;
  component_id: string;         // node_id
  source_evidence: string;      // "file.py:42"
  expected_behavior: string;
  proposed_test_file: string;   // relative path in working_copy
  proposed_test_function: string;
}

interface ExistingTestMapping {
  node_id: string;
  test_files: string[];
  coverage_status: "covered" | "indirect" | "none";
}
```

### POST /api/v1/sessions/{id}/tests/approve — Request

```typescript
interface ApprovePlanRequest {
  plan_id: string;
  approved: true;               // literal true required
}
```

### TestRunResult (GET /api/v1/sessions/{id}/tests/results)

```typescript
interface TestRunResult {
  run_id: string;
  plan_id: string;
  session_id: string;
  component_statuses: ComponentTestStatus[];
  test_results: TestCaseResult[];
  sandbox_exit_code: number;
  infrastructure_error: string | null;
}

interface ComponentTestStatus {
  node_id: string;
  status: "covered_passed" | "covered_failed" | "unexecuted" | "no_suitable_test";
  test_count: number;
  passed: number;
  failed: number;
}

interface TestCaseResult {
  test_id: string;
  test_file: string;
  test_function: string;
  status: "passed" | "failed" | "error" | "skipped";
  stdout: string;
  stderr: string;
  duration_ms: number;
  linked_node_ids: string[];    // graph nodes this test covers
}
```

---

## 7. Verification & Documentation

### VerificationReport (GET /api/v1/sessions/{id}/verification)

```typescript
interface VerificationReport {
  report_id: string;
  session_id: string;
  components_verified: ComponentVerification[];
  unresolved_risks: UnresolvedRisk[];
  documentation_gaps: DocumentationGap[];
  pr_summary: string;           // Markdown
  generated_at: string;         // ISO 8601
}

interface ComponentVerification {
  component_id: string;         // node_id
  status: "passed" | "failed" | "unexecuted" | "no_test";
  evidence_refs: EvidenceRef[];
}

interface UnresolvedRisk {
  hypothesis: string;
  component_id: string;
  reason_unresolved: string;
}

interface DocumentationGap {
  file: string;
  current_text: string;
  proposed_text: string;
  reason: string;
  patch_file: string | null;    // relative path in working_copy
}
```

---

## 8. Bob Agent Output Schemas

These are the Pydantic schemas the backend validates Bob responses against. They are defined in `backend/app/bob/schemas/`.

### ArchitectureFindings

```python
class NodeSummary(BaseModel):
    node_id: str
    summary: str
    key_responsibilities: list[str]

class ArchitectureFindings(BaseModel):
    entry_points: list[str]           # node_ids
    node_summaries: list[NodeSummary]
    architectural_patterns: list[str]
    concerns: list[str]               # e.g., "circular dependency detected"
```

### DocumentationFindings

```python
class DocumentationIssue(BaseModel):
    file: str
    issue: str
    severity: Literal["error", "warning", "info"]

class DocumentationFindings(BaseModel):
    issues: list[DocumentationIssue]
    setup_completeness: Literal["complete", "partial", "missing"]
    notes: list[str]
```

### EnvironmentDiagnosis

```python
class EnvironmentDiagnosis(BaseModel):
    root_cause: str
    proposed_fix: str
    patch: str | None             # unified diff or None
    confidence: Literal["high", "medium", "low"]
    references: list[str]         # file paths or README sections
```

### ImpactAnnotations

```python
class ImpactAnnotation(BaseModel):
    node_id: str
    risk: str
    hypothesis_label: str = "hypothesis"
    evidence_status: Literal["inferred"] = "inferred"

class ImpactAnnotations(BaseModel):
    annotations: list[ImpactAnnotation]
    analysis_notes: list[str]
```

### TestPlanProposal (Bob output)

```python
class TestScenarioBob(BaseModel):
    name: str
    component_id: str
    source_evidence: str
    expected_behavior: str
    proposed_test_file: str
    proposed_test_function: str

class TestPlanProposalBob(BaseModel):
    scenarios: list[TestScenarioBob]
    rationale: str
    coverage_notes: list[str]
```

### ContributionGuidance

```python
class ImplementationStep(BaseModel):
    step_number: int
    description: str
    file: str | None
    line: int | None
    hint: str

class ContributionGuidance(BaseModel):
    steps: list[ImplementationStep]
    hints: list[str]
    caveats: list[str]
    relevant_tests: list[str]         # test file paths
```

### VerificationReport (Bob output)

```python
class ComponentVerificationBob(BaseModel):
    component_id: str
    status: Literal["passed", "failed", "unexecuted", "no_test"]
    evidence_refs: list[str]          # "file:line" strings

class UnresolvedRiskBob(BaseModel):
    hypothesis: str
    component_id: str
    reason_unresolved: str

class DocumentationGapBob(BaseModel):
    file: str
    current_text: str
    proposed_text: str
    reason: str

class VerificationReportBob(BaseModel):
    components_verified: list[ComponentVerificationBob]
    unresolved_risks: list[UnresolvedRiskBob]
    documentation_gaps: list[DocumentationGapBob]
    pr_summary: str
```

---

## 9. WebSocket Events

Endpoint: `ws/sessions/{session_id}/events`

All events are JSON objects with a common envelope:

```typescript
interface WsEvent {
  event_type: WsEventType;
  session_id: string;
  timestamp: string;          // ISO 8601
  payload: unknown;           // type depends on event_type
}

type WsEventType =
  | "session_status_changed"
  | "agent_started"
  | "agent_completed"
  | "agent_failed"
  | "container_log"
  | "step_status_changed"
  | "test_result";
```

### Payload shapes by event type

```typescript
// session_status_changed
{ new_status: SessionStatus }

// agent_started / agent_completed / agent_failed
{ agent: string; duration_ms?: number; error?: string }

// container_log
{ stream: "stdout" | "stderr"; text: string; step_index: number }

// step_status_changed
{ step_index: number; status: EnvironmentCheck["status"] }

// test_result
{ test_function: string; status: TestCaseResult["status"] }
```

> **Open question (ARCHITECTURE.md §11 item 7):** This schema is a proposal. The exact event format must be validated against Bob's available streaming interface before implementation.

---

## 10. Error Responses

All error responses follow a standard envelope:

```typescript
interface ErrorResponse {
  error: string;              // machine-readable code: "not_found", "approval_required", etc.
  message: string;            // human-readable description
  detail: unknown | null;     // optional structured detail
}
```

### HTTP status codes used

| Code | When |
|---|---|
| 400 | Invalid request (both `symbol_id` and `git_diff` provided, etc.) |
| 404 | Session, run, or node not found |
| 409 | Conflicting state (e.g., X-Ray already running) |
| 412 | Precondition failed (e.g., X-Ray must complete before FirstPR) |
| 422 | Request body validation failed (Pydantic) |
| 500 | Unexpected server error |
| 503 | Bob integration unavailable |
