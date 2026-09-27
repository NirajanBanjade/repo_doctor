import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getTestPlan, approveTestPlan, runTests, refinePlan } from "@/api/client";
import ApprovalModal from "@/components/ApprovalModal";
import Spinner from "@/components/Spinner";
import type { TestScenario, ExistingTestMapping } from "@/types";

const COVERAGE_COLOR: Record<ExistingTestMapping["coverage_status"], string> = {
  covered: "var(--success)",
  indirect: "var(--warning)",
  none: "var(--danger)",
};

interface Props {
  sessionId: string;
  onRan?: () => void;
}

export default function TestPlanView({ sessionId, onRan }: Props) {
  const qc = useQueryClient();
  const [showApproval, setShowApproval] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [expandedScenario, setExpandedScenario] = useState<string | null>(null);

  const {
    data: plan,
    isPending,
    error,
  } = useQuery({
    queryKey: ["testplan", sessionId],
    queryFn: () => getTestPlan(sessionId),
    retry: false,
  });

  const { mutate: approve, isPending: isApproving } = useMutation({
    mutationFn: () =>
      approveTestPlan(sessionId, { plan_id: plan!.plan_id, approved: true }),
    onSuccess: (updatedPlan) => {
      setShowApproval(false);
      qc.setQueryData(["testplan", sessionId], updatedPlan);
    },
  });

  const { mutate: runAll, isPending: isRunning } = useMutation({
    mutationFn: () => runTests(sessionId, plan!.plan_id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["testresults", sessionId] });
      void qc.invalidateQueries({ queryKey: ["verification", sessionId] });
      onRan?.();
    },
  });

  const { mutate: refine, isPending: isRefining } = useMutation({
    mutationFn: () => refinePlan(sessionId, plan!.plan_id, feedback),
    onSuccess: (updated) => {
      qc.setQueryData(["testplan", sessionId], updated);
      setFeedback("");
    },
  });

  if (isPending) {
    return (
      <div style={{ display: "flex", gap: 10, alignItems: "center", padding: 32 }}>
        <Spinner /> Loading test plan…
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div style={{ padding: 32, color: "var(--muted)" }}>
        No test plan yet. Run Impact Scope, choose feature files, and create a plan.
      </div>
    );
  }

  const isPlanApproved = plan.status === "approved";
  const isPlanProposed = plan.status === "proposed";

  return (
    <div style={{ padding: 24, maxWidth: 820 }}>

      {/* ── Header ── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
        }}
      >
        <div>
          <h2 style={{ marginBottom: 4 }}>Test Plan</h2>
          <p style={{ fontSize: 13, color: "var(--muted)", margin: 0 }}>
            Bob analysed the selected files and proposed the scenarios below.
            Review them, refine if needed, then approve to generate test files.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0, marginLeft: 16 }}>
          {isPlanProposed && (
            <button className="btn btn-primary" onClick={() => setShowApproval(true)}>
              Approve &amp; Generate Tests
            </button>
          )}
          {isPlanApproved && (
            <button
              className="btn btn-primary"
              onClick={() => runAll()}
              disabled={isRunning}
            >
              {isRunning ? (
                <>
                  <Spinner size={13} /> Running tests…
                </>
              ) : (
                "Run Tests"
              )}
            </button>
          )}
        </div>
      </div>

      {/* ── Status badge ── */}
      <div style={{ marginBottom: 20 }}>
        <span
          style={{
            padding: "3px 12px",
            borderRadius: 12,
            fontSize: 12,
            fontWeight: 600,
            background:
              plan.status === "approved"
                ? "#dcfce7"
                : plan.status === "rejected"
                  ? "#fee2e2"
                  : "#eff6ff",
            color:
              plan.status === "approved"
                ? "var(--success)"
                : plan.status === "rejected"
                  ? "var(--danger)"
                  : "var(--accent)",
            border: "1px solid transparent",
          }}
        >
          {plan.status.toUpperCase()}
        </span>
      </div>

      {isPlanApproved && (
        <div
          style={{
            marginBottom: 20,
            padding: "12px 16px",
            background: plan.generated_files.length > 0 ? "#f0fdf4" : "#fff1f2",
            border: `1px solid ${plan.generated_files.length > 0 ? "#86efac" : "#fca5a5"}`,
            borderRadius: "var(--radius)",
            fontSize: 13,
          }}
        >
          <strong>
            {plan.generated_files.length > 0
              ? `${plan.generated_files.length} test file(s) generated`
              : "Test generation failed"}
          </strong>
          {plan.generated_files.map((file) => (
            <p key={file} className="mono" style={{ fontSize: 11, marginTop: 5 }}>
              {file}
            </p>
          ))}
        </div>
      )}

      {/* ── Bob's overall rationale ── */}
      {plan.overall_rationale && (
        <div
          style={{
            marginBottom: 20,
            padding: "12px 16px",
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: "var(--radius)",
            fontSize: 13,
            lineHeight: 1.6,
          }}
        >
          <p style={{ fontWeight: 600, marginBottom: 4, color: "var(--accent)" }}>
            Bob's analysis
          </p>
          <p style={{ margin: 0, color: "var(--text)" }}>{plan.overall_rationale}</p>
        </div>
      )}

      {/* ── Analysis notes ── */}
      {plan.analysis_notes.length > 0 && (
        <div
          style={{
            marginBottom: 20,
            padding: "10px 14px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
          }}
        >
          <p style={{ fontWeight: 600, fontSize: 12, marginBottom: 6 }}>Notes</p>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {plan.analysis_notes.map((note, i) => (
              <li key={i} style={{ fontSize: 12, color: "var(--muted)", marginBottom: 3 }}>
                {note}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Coverage gaps ── */}
      {plan.coverage_gaps.length > 0 && (
        <div
          style={{
            marginBottom: 20,
            padding: "10px 14px",
            background: "#fff1f2",
            border: "1px solid #fca5a5",
            borderRadius: "var(--radius)",
            fontSize: 13,
          }}
        >
          <strong>Coverage gaps</strong> — {plan.coverage_gaps.length} node(s) have no
          existing test:
          <ul style={{ margin: "6px 0 0 18px" }}>
            {plan.coverage_gaps.map((n) => (
              <li key={n} className="mono" style={{ fontSize: 12 }}>
                {n}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Proposed scenarios ── */}
      <h3 style={{ marginBottom: 12 }}>
        Proposed Test Scenarios ({plan.scenarios.length})
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 28 }}>
        {plan.scenarios.length === 0 && (
          <p style={{ color: "var(--muted)", fontSize: 13 }}>
            No scenarios yet — Bob could not generate a plan (Bob unavailable). You can
            still approve an empty plan or add feedback below to retry.
          </p>
        )}
        {plan.scenarios.map((scenario: TestScenario, idx) => {
          const isOpen = expandedScenario === scenario.scenario_id;
          return (
            <div
              key={scenario.scenario_id ?? idx}
              style={{
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                overflow: "hidden",
                background: "var(--bg)",
              }}
            >
              {/* Scenario header — always visible */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  padding: "12px 14px",
                  cursor: "pointer",
                  background: isOpen ? "var(--surface)" : "var(--bg)",
                }}
                onClick={() =>
                  setExpandedScenario(isOpen ? null : (scenario.scenario_id ?? String(idx)))
                }
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                    {idx + 1}. {scenario.name}
                  </p>
                  <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>
                    {scenario.expected_behavior}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0, marginLeft: 12 }}>
                  <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                    {scenario.proposed_test_function}
                  </span>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>
                    {isOpen ? "▲" : "▼"}
                  </span>
                </div>
              </div>

              {/* Expanded detail */}
              {isOpen && (
                <div
                  style={{
                    padding: "12px 14px",
                    borderTop: "1px solid var(--border)",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                  }}
                >
                  {/* Rationale */}
                  {scenario.rationale && (
                    <div>
                      <p style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)", marginBottom: 3 }}>
                        Why this test matters
                      </p>
                      <p style={{ fontSize: 12, color: "var(--text)", margin: 0 }}>
                        {scenario.rationale}
                      </p>
                    </div>
                  )}

                  {/* Edge cases */}
                  {scenario.edge_cases.length > 0 && (
                    <div>
                      <p style={{ fontSize: 11, fontWeight: 600, color: "var(--secondary)", marginBottom: 3 }}>
                        Edge cases Bob will cover
                      </p>
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {scenario.edge_cases.map((ec, i) => (
                          <li key={i} style={{ fontSize: 12, color: "var(--text)", marginBottom: 2 }}>
                            {ec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* File info */}
                  <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                    <div>
                      <p style={{ fontSize: 11, color: "var(--muted)", marginBottom: 2 }}>Component</p>
                      <p className="mono" style={{ fontSize: 11 }}>{scenario.component_id}</p>
                    </div>
                    <div>
                      <p style={{ fontSize: 11, color: "var(--muted)", marginBottom: 2 }}>Test file</p>
                      <p className="mono" style={{ fontSize: 11 }}>{scenario.proposed_test_file}</p>
                    </div>
                    <div>
                      <p style={{ fontSize: 11, color: "var(--muted)", marginBottom: 2 }}>Evidence</p>
                      <p className="mono" style={{ fontSize: 11 }}>{scenario.source_evidence}</p>
                    </div>
                    {scenario.generation_status && (
                      <div>
                        <p style={{ fontSize: 11, color: "var(--muted)", marginBottom: 2 }}>Generation</p>
                        <p style={{ fontSize: 11 }}>{scenario.generation_status}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Existing test coverage ── */}
      {plan.existing_test_mappings.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 8 }}>Existing Test Coverage</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {plan.existing_test_mappings.map((m) => (
              <div
                key={m.node_id}
                style={{
                  display: "flex",
                  gap: 10,
                  alignItems: "flex-start",
                  padding: "8px 12px",
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius)",
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: COVERAGE_COLOR[m.coverage_status],
                    whiteSpace: "nowrap",
                    padding: "2px 6px",
                    background: COVERAGE_COLOR[m.coverage_status] + "1a",
                    borderRadius: 10,
                    marginTop: 1,
                  }}
                >
                  {m.coverage_status}
                </span>
                <div>
                  <p className="mono" style={{ fontSize: 12, marginBottom: 2 }}>
                    {m.node_id}
                  </p>
                  {m.test_files.map((f) => (
                    <p key={f} style={{ fontSize: 11, color: "var(--muted)" }}>
                      {f}
                    </p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Refine with feedback (only while proposed) ── */}
      {isPlanProposed && (
        <div
          style={{
            marginBottom: 24,
            padding: "16px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
          }}
        >
          <p style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
            Ask Bob to refine the plan
          </p>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>
            Tell Bob what to add, remove, or change — e.g. "add edge cases for null
            inputs", "focus only on the payment module", "add a scenario for the error
            path in submit_order".
          </p>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Your feedback to Bob…"
            rows={3}
            style={{ width: "100%", marginBottom: 8, resize: "vertical", boxSizing: "border-box" }}
          />
          <button
            className="btn btn-secondary"
            disabled={isRefining || !feedback.trim()}
            onClick={() => refine()}
          >
            {isRefining ? (
              <>
                <Spinner size={13} /> Refining…
              </>
            ) : (
              "Refine Plan"
            )}
          </button>
        </div>
      )}

      {/* ── External feature suggestions ── */}
      {(plan.external_feature_suggestions?.length ?? 0) > 0 && (
        <div
          style={{
            marginBottom: 20,
            padding: 12,
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
          }}
        >
          <strong>Optional cross-feature regression tests</strong>
          <p className="text-muted" style={{ fontSize: 12, margin: "4px 0 8px" }}>
            These connected features are outside the primary plan and were not added
            automatically.
          </p>
          {plan.external_feature_suggestions!.map((feature) => (
            <div key={feature.feature_id} style={{ fontSize: 12 }}>
              {feature.name} — {feature.reason}
            </div>
          ))}
        </div>
      )}

      {/* ── Approval modal ── */}
      {showApproval && (
        <ApprovalModal
          title="Approve Test Plan"
          message={`Approving this plan will generate ${plan.scenarios.length} test file(s) in the working copy. The original repository will not be modified, and the tests will not run until you click Run Tests.`}
          confirmLabel="Approve & Generate"
          onConfirm={() => approve()}
          onCancel={() => setShowApproval(false)}
          isLoading={isApproving}
        />
      )}
    </div>
  );
}
