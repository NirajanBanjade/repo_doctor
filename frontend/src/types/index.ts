// Core domain types — matches docs/api/contracts.md exactly

export interface GraphNode {
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

export interface GraphEdge {
  edge_id: string;
  source_id: string;
  target_id: string;
  relationship: "calls" | "imports" | "inherits" | "uses";
  file: string;
  line: number;
  evidence_status: "confirmed_static" | "observed_test" | "inferred";
  note: string | null;
}

export interface EvidenceRef {
  file: string;
  line: number;
  snippet: string | null;
  evidence_status: "confirmed_static" | "observed_test" | "inferred";
}

export interface StarterTask {
  id: string;
  title: string;
  description: string;
  target_symbol: string;
  target_file: string;
  target_line: number;
  recommended_impact_depth: 1 | 2 | 3;
}

// Session types
export type SessionStatus =
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

export interface StackDetection {
  language: string;
  framework: string | null;
  test_runner: string | null;
  adapter_available: boolean;
}

export interface Session {
  session_id: string;
  status: SessionStatus;
  repo_path: string;
  architecture_path?: string;
  stack: StackDetection | null;
  created_at: string;
  updated_at: string;
}

export interface CreateSessionRequest {
  repo_path: string;
  architecture_path: string;
}

export interface FeatureArchitecture {
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

// X-Ray types
export interface XRayResult {
  session_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  features: FeatureArchitecture[];
  architecture_findings: ArchitectureFindings | null;
  documentation_findings: DocumentationFindings | null;
  warnings: string[];
}

export interface NodeSummary {
  node_id: string;
  summary: string;
  key_responsibilities: string[];
}

export interface ArchitectureFindings {
  entry_points: string[];
  node_summaries: NodeSummary[];
  architectural_patterns: string[];
  concerns: string[];
}

export interface DocumentationIssue {
  file: string;
  issue: string;
  severity: "error" | "warning" | "info";
}

export interface DocumentationFindings {
  issues: DocumentationIssue[];
  setup_completeness: "complete" | "partial" | "missing";
  notes: string[];
}

// Environment Doctor types
export interface EnvironmentCheck {
  check_id: string;
  session_id: string;
  step_index: number;
  command: string;
  stdout: string;
  stderr: string;
  exit_code: number;
  status: "verified" | "failed" | "blocked" | "infrastructure_error";
  verified_at: string | null;
}

export interface EnvironmentDiagnosis {
  root_cause: string;
  proposed_fix: string;
  patch: string | null;
  confidence: "high" | "medium" | "low";
  references: string[];
}

export interface EnvironmentRunResult {
  session_id: string;
  run_id: string;
  checks: EnvironmentCheck[];
  all_verified: boolean;
  diagnosis: EnvironmentDiagnosis | null;
}

export interface ApplyFixRequest {
  step_id: string;
  approval: true;
  patch_content: string | null;
}

// ImpactScope types
export interface ImpactRequest {
  symbol_id?: string;
  feature_id?: string;
  file_path?: string;
  git_diff?: string;
  change_description?: string;
  depth: 1 | 2 | 3;
}

export interface ImpactNode {
  node_id: string;
  depth_level: number;
  node: GraphNode;
  existing_tests: string[];
}

export interface ImpactAnnotation {
  node_id: string;
  risk: string;
  hypothesis_label: string;
  evidence_status: "inferred";
}

export interface ImpactRunResult {
  run_id: string;
  session_id: string;
  origin_ids: string[];
  depth: 1 | 2 | 3;
  change_description: string | null;
  nodes: ImpactNode[];
  edges: GraphEdge[];
  annotations: ImpactAnnotation[];
  unresolved_symbols: string[];
  warnings: string[];
  primary_feature?: { feature_id: string; name: string } | null;
  external_feature_suggestions?: Array<{
    feature_id: string;
    name: string;
    reason: string;
  }>;
}

// Test types
export interface TestScenario {
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

export interface ExistingTestMapping {
  node_id: string;
  test_files: string[];
  coverage_status: "covered" | "indirect" | "none";
}

export interface TestPlanProposal {
  plan_id: string;
  session_id: string;
  impact_run_id: string;
  status: "proposed" | "approved" | "rejected";
  scenarios: TestScenario[];
  analysis_notes: string[];
  overall_rationale: string;
  existing_test_mappings: ExistingTestMapping[];
  coverage_gaps: string[];
  selected_node_ids: string[];
  generated_files: string[];
  external_feature_suggestions?: Array<{
    feature_id: string;
    name: string;
    reason: string;
  }>;
}

export interface ApprovePlanRequest {
  plan_id: string;
  approved: true;
}

export interface ComponentTestStatus {
  node_id: string;
  status: "covered_passed" | "covered_failed" | "unexecuted" | "no_suitable_test";
  test_count: number;
  passed: number;
  failed: number;
}

export interface TestCaseResult {
  test_id: string;
  test_file: string;
  test_function: string;
  status: "passed" | "failed" | "error" | "skipped";
  stdout: string;
  stderr: string;
  duration_ms: number;
  linked_node_ids: string[];
}

export interface TestRunResult {
  run_id: string;
  plan_id: string;
  session_id: string;
  component_statuses: ComponentTestStatus[];
  test_results: TestCaseResult[];
  sandbox_exit_code: number;
  infrastructure_error: string | null;
}

// Verification types
export interface ComponentVerification {
  component_id: string;
  status: "passed" | "failed" | "unexecuted" | "no_test";
  evidence_refs: EvidenceRef[];
}

export interface UnresolvedRisk {
  hypothesis: string;
  component_id: string;
  reason_unresolved: string;
}

export interface DocumentationGap {
  file: string;
  current_text: string;
  proposed_text: string;
  reason: string;
  patch_file: string | null;
}

export interface VerificationReport {
  report_id: string;
  session_id: string;
  components_verified: ComponentVerification[];
  unresolved_risks: UnresolvedRisk[];
  documentation_gaps: DocumentationGap[];
  pr_summary: string;
  generated_at: string;
}

// WebSocket event types
export type WsEventType =
  | "session_status_changed"
  | "agent_started"
  | "agent_completed"
  | "agent_failed"
  | "container_log"
  | "step_status_changed"
  | "test_result";

export interface WsEvent {
  event_type: WsEventType;
  session_id: string;
  timestamp: string;
  payload: unknown;
}

// Error response
export interface ErrorResponse {
  error: string;
  message: string;
  detail: unknown | null;
}
