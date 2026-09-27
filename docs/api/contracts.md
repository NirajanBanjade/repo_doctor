# RepoDoc — Current REST and Data Contracts

All implemented endpoints are under `/api/v1/sessions`. Examples below show the
stable fields consumed by the current frontend; backend responses may include the
additional warning/detail fields noted here.

## 1. Core Graph Types

```ts
interface GraphNode {
  node_id: string;
  kind: "function" | "class" | "module" | "file";
  name: string;
  path: string;
  line_start: number;
  line_end: number;
  language: string;
  summary: string | null;
  key_module: boolean;
}

interface GraphEdge {
  edge_id: string;
  source_id: string;
  target_id: string;
  relationship: "calls" | "imports" | "inherits" | "uses";
  file: string;
  line: number;
  evidence_status: "confirmed_static" | "observed_test" | "inferred";
  note: string | null;
}
```

`observed_test` is a reserved value and is not currently produced by execution.

## 2. Sessions

### `POST /api/v1/sessions`

```ts
interface CreateSessionRequest {
  repo_path: string;
  architecture_path?: string; // absolute or relative to repo_path
}
```

The repository must exist and be a directory. When supplied, the architecture path
must be a directory containing a non-README `.md` page.

### `GET /api/v1/sessions/{session_id}`

```ts
interface Session {
  session_id: string;
  repo_path: string;
  status: string;
  stack: {
    language?: string;
    framework?: string | null;
    test_runner?: string | null;
    adapter_available?: boolean;
    architecture_path?: string;
  } | null;
  created_at: string;
  updated_at: string;
}
```

## 3. Repository X-Ray

### `POST /api/v1/sessions/{session_id}/xray` — `202`

Returns `session_id`, `status`, `node_count`, `edge_count`, and `warnings` after the
current inline analysis completes.

### `GET /api/v1/sessions/{session_id}/xray/graph`

```ts
interface FeatureArchitecture {
  feature_id: string;
  name: string;
  description: string;
  document: string;
  frontend_files: string[];
  backend_files: string[];
  files: string[];
  file_edges: Array<{ source: string; target: string }>;
  connected_feature_ids: string[];
}

interface XRayResult {
  session_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  features: FeatureArchitecture[];
  architecture_findings: ArchitectureFindings | null;
  documentation_findings: DocumentationFindings | null;
  warnings: string[];
}
```

Agent finding fields are currently `null` because the Bob transport is unwired.

## 4. Environment Doctor

### `POST /api/v1/sessions/{session_id}/environment/run` — `202`

Returns `{session_id, status, run_number?, steps, warnings}`. `status` can be
`verified`, `failed`, `partial`, `infrastructure_error`, or `no_steps`.

### `POST /api/v1/sessions/{session_id}/environment/fix` — `202`

```ts
interface FixRequest {
  step_id: string;
  fix_description: string;
  patch_content?: string | null;
  approval: boolean; // must be true
}
```

### `GET /api/v1/sessions/{session_id}/environment/checks`

Optional query: `run_number`. Returns persisted step history.

### `GET /api/v1/sessions/{session_id}/environment/status`

```ts
interface EnvironmentRunResult {
  session_id: string;
  run_id: string;
  checks: Array<{
    check_id: string;
    session_id: string;
    step_index: number;
    command: string;
    stdout: string;
    stderr: string;
    exit_code: number | null;
    status: "verified" | "failed" | "blocked" | "infrastructure_error";
    verified_at: string | null;
  }>;
  all_verified: boolean;
  diagnosis: null; // current retrieval behavior
}
```

## 5. ImpactScope

### `POST /api/v1/sessions/{session_id}/impact` — `202`

```ts
interface ImpactRequest {
  symbol_id?: string;
  feature_id?: string;
  file_path?: string;
  git_diff?: string;
  change_description?: string;
  depth: 1 | 2 | 3;
}
```

Exactly one origin field is required.

```ts
interface ImpactRunResult {
  run_id: string;
  session_id: string;
  origin_ids: string[];
  depth: 1 | 2 | 3;
  change_description: string | null;
  nodes: Array<{
    node_id: string;
    depth_level: number;
    node: GraphNode;
    existing_tests: string[];
  }>;
  edges: GraphEdge[];
  annotations: Array<{
    node_id: string;
    risk: string;
    hypothesis_label: string;
    evidence_status: "inferred";
  }>;
  unresolved_symbols: string[];
  warnings: string[];
  primary_feature: { feature_id: string; name: string } | null;
  external_feature_suggestions: Array<{
    feature_id: string;
    name: string;
    reason: string;
  }>;
}
```

`GET /api/v1/sessions/{session_id}/impact/graph` returns the latest run.

## 6. Test Plans

### `POST /api/v1/sessions/{session_id}/tests/plan` — `202`

```ts
interface PlanRequest {
  impact_run_id: string;
  selected_node_ids: string[];
  change_description?: string;
  diff_content?: string;
}
```

### Plan response

```ts
interface TestScenario {
  scenario_id: string;
  name: string;
  component_id: string;
  source_evidence: string;
  expected_behavior: string;
  proposed_test_file: string;
  proposed_test_function: string;
  rationale: string;
  edge_cases: string[];
  generation_status?: "generated" | "failed";
  generated_test_file?: string;
}

interface TestPlanProposal {
  plan_id: string;
  session_id: string;
  impact_run_id: string;
  status: "proposed" | "approved" | "rejected";
  scenarios: TestScenario[];
  analysis_notes: string[];
  overall_rationale: string;
  existing_test_mappings: Array<{
    node_id: string;
    test_files: string[];
    coverage_status: "covered" | "indirect" | "none";
  }>;
  coverage_gaps: string[];
  selected_node_ids: string[];
  generated_files: string[];
  external_feature_suggestions: Array<{
    feature_id: string;
    name: string;
    reason: string;
  }>;
}
```

`GET /tests/plan` returns the plan for the latest impact run.

### `POST /tests/plan/{plan_id}/refine`

Body: `{ "feedback": string }`. Only a `proposed` plan can be refined.

### `POST /tests/plan/{plan_id}/approve`

Body: `{ "plan_id": string, "approved": boolean }`. Approval generates files;
rejection does not. Only a `proposed` plan can be reviewed.

### `POST /tests/plan/{plan_id}/run` — `202`

Requires an approved plan and present generated files.

### Test result

The run endpoint returns backend-oriented keys (`result_id`, `per_test`,
`generated_files`, `warnings`). `GET /tests/results` returns the frontend contract:

```ts
interface TestRunResult {
  run_id: string;
  plan_id: string;
  session_id: string;
  component_statuses: Array<{
    component_id: string;
    node_id: string;
    status: "covered_passed" | "covered_failed" | "unexecuted" | "no_suitable_test";
    test_count: number;
    passed: number;
    failed: number;
  }>;
  test_results: Array<{
    test_id: string;
    test_file: string;
    test_function: string;
    status: "passed" | "failed" | "error" | "skipped";
    stdout: string;
    stderr: string;
    duration_ms: number;
    linked_node_ids: string[];
  }>;
  sandbox_exit_code: number | null;
  infrastructure_error: string | null;
}
```

`GET /tests/plan/{plan_id}/result` returns the stored backend-oriented result.

## 7. Verification

### `GET /api/v1/sessions/{session_id}/verification`

This GET creates and stores the first report, then returns the cached report on later
calls.

```ts
interface VerificationReport {
  report_id: string;
  session_id: string;
  components_verified: Array<{
    component_id: string;
    status: "passed" | "failed" | "unexecuted" | "no_test";
    evidence_refs: Array<{
      file: string;
      line: number;
      snippet: string | null;
      evidence_status: "confirmed_static" | "observed_test" | "inferred";
    }>;
  }>;
  unresolved_risks: Array<{
    hypothesis: string;
    component_id: string;
    reason_unresolved: string;
  }>;
  documentation_gaps: Array<{
    file: string;
    current_text: string;
    proposed_text: string;
    reason: string;
  }>;
  pr_summary: string;
  patch_paths: string[];
  disclaimer: string;
}
```

## 8. Bob Output Schemas

Pydantic schemas exist for `ArchitectureFindings`, `DocumentationFindings`,
`EnvironmentDiagnosis`, `ImpactAnnotations`, `TestPlanProposal`, and
`VerificationReport`. The backend stores every attempted raw result in `bob_outputs`.
Unavailable and invalid results use `parsed_ok=false` and are not consumed as
structured data.

There is no implemented Contribution Agent schema.

## 9. Errors and Unimplemented Contracts

FastAPI returns `{ "detail": ... }` for route errors. Common codes are `400` for a
missing approval flag, `403` for cross-session ownership, `404` for missing records,
`422` for invalid state/input, and `500` for unexpected X-Ray errors.

No FirstPR or WebSocket endpoint is registered. Their dormant frontend types must not
be treated as live API contracts.
