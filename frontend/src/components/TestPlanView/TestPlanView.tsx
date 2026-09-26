import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getTestPlan, approveTestPlan, runTests } from "@/api/client";
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
  onApproved?: () => void;
}

export default function TestPlanView({ sessionId, onApproved }: Props) {
  const qc = useQueryClient();
  const [showApproval, setShowApproval] = useState(false);

  const { data: plan, isPending, error } = useQuery({
    queryKey: ["testplan", sessionId],
    queryFn: () => getTestPlan(sessionId),
  });

  const { mutate: approve, isPending: isApproving } = useMutation({
    mutationFn: () =>
      approveTestPlan(sessionId, { plan_id: plan!.plan_id, approved: true }),
    onSuccess: () => {
      setShowApproval(false);
      void qc.invalidateQueries({ queryKey: ["testplan", sessionId] });
      onApproved?.();
    },
  });

  const { mutate: runAll, isPending: isRunning } = useMutation({
    mutationFn: () => runTests(sessionId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["testresults", sessionId] });
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
        No test plan yet. Run an impact analysis first.
      </div>
    );
  }

  const isPlanApproved = plan.status === "approved";

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2>Test Plan</h2>
        <div style={{ display: "flex", gap: 8 }}>
          {!isPlanApproved && (
            <button
              className="btn btn-primary"
              onClick={() => setShowApproval(true)}
            >
              Approve Plan
            </button>
          )}
          {isPlanApproved && (
            <button
              className="btn btn-primary"
              onClick={() => runAll()}
              disabled={isRunning}
            >
              {isRunning ? <><Spinner size={13} /> Running tests…</> : "Run Tests"}
            </button>
          )}
        </div>
      </div>

      {/* Status badge */}
      <div style={{ marginBottom: 16 }}>
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
                  : "#fef9c3",
            color:
              plan.status === "approved"
                ? "var(--success)"
                : plan.status === "rejected"
                  ? "var(--danger)"
                  : "var(--warning)",
            border: "1px solid transparent",
          }}
        >
          {plan.status.toUpperCase()}
        </span>
      </div>

      {/* Coverage gaps */}
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
          <strong>Coverage gaps</strong> — {plan.coverage_gaps.length} node(s) have no existing test:
          <ul style={{ margin: "6px 0 0 18px" }}>
            {plan.coverage_gaps.map((n) => (
              <li key={n} className="mono" style={{ fontSize: 12 }}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Existing test mappings */}
      {plan.existing_test_mappings.length > 0 && (
        <div style={{ marginBottom: 20 }}>
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

      {/* Proposed scenarios */}
      <h3 style={{ marginBottom: 10 }}>
        Proposed Scenarios ({plan.scenarios.length})
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {plan.scenarios.map((scenario: TestScenario) => (
          <div
            key={scenario.scenario_id}
            style={{
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              padding: "12px 14px",
              background: "var(--bg)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <strong style={{ fontSize: 13 }}>{scenario.name}</strong>
              <span className="mono text-muted" style={{ fontSize: 11 }}>
                {scenario.proposed_test_function}
              </span>
            </div>
            <p style={{ fontSize: 12, marginBottom: 6, color: "var(--text)" }}>
              {scenario.expected_behavior}
            </p>
            <p className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
              {scenario.proposed_test_file} · source: {scenario.source_evidence}
            </p>
          </div>
        ))}
      </div>

      {/* Approval modal */}
      {showApproval && (
        <ApprovalModal
          title="Approve Test Plan"
          message={`This will generate ${plan.scenarios.length} test file(s) in the working copy and execute them inside the sandbox. The original repository is never modified. Proceed?`}
          confirmLabel="Approve & Continue"
          onConfirm={() => approve()}
          onCancel={() => setShowApproval(false)}
          isLoading={isApproving}
        />
      )}
    </div>
  );
}
