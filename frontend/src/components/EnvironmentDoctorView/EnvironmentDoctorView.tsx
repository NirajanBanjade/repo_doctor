import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  runEnvironment,
  getEnvironmentStatus,
  applyEnvironmentFix,
} from "@/api/client";
import Spinner from "@/components/Spinner";
import ApprovalModal from "@/components/ApprovalModal";
import type { EnvironmentCheck } from "@/types";

const STATUS_ICON: Record<EnvironmentCheck["status"], string> = {
  verified: "✓",
  failed: "✗",
  blocked: "⚠",
  infrastructure_error: "⚡",
};

const STATUS_COLOR: Record<EnvironmentCheck["status"], string> = {
  verified: "var(--success)",
  failed: "var(--danger)",
  blocked: "var(--warning)",
  infrastructure_error: "var(--secondary)",
};

interface Props {
  sessionId: string;
}

export default function EnvironmentDoctorView({ sessionId }: Props) {
  const qc = useQueryClient();
  const [fixStepId, setFixStepId] = useState<string | null>(null);
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  const {
    data: envResult,
    isPending,
    error,
  } = useQuery({
    queryKey: ["environment", sessionId],
    queryFn: () => getEnvironmentStatus(sessionId),
  });

  const { mutate: startRun, isPending: isStarting } = useMutation({
    mutationFn: () => runEnvironment(sessionId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["environment", sessionId] });
    },
  });

  const { mutate: applyFix, isPending: isApplying } = useMutation({
    mutationFn: (stepId: string) =>
      applyEnvironmentFix(sessionId, {
        step_id: stepId,
        approval: true,
        patch_content: null,
      }),
    onSuccess: () => {
      setFixStepId(null);
      void qc.invalidateQueries({ queryKey: ["environment", sessionId] });
    },
  });

  if (isPending) {
    return (
      <div style={{ display: "flex", gap: 10, alignItems: "center", padding: 32 }}>
        <Spinner /> Loading environment status…
      </div>
    );
  }

  if (error || !envResult || envResult.checks.length === 0) {
    return (
      <div style={{ padding: 32 }}>
        <p className="text-muted" style={{ marginBottom: 12 }}>
          No environment run yet. Start the Environment Doctor to verify your setup.
        </p>
        <button
          className="btn btn-primary"
          onClick={() => startRun()}
          disabled={isStarting}
        >
          {isStarting ? (
            <>
              <Spinner size={14} /> Running…
            </>
          ) : (
            "Run Environment Doctor"
          )}
        </button>
      </div>
    );
  }

  const allVerified = envResult.all_verified;

  return (
    <div style={{ padding: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h2>Environment Doctor</h2>
        <button
          className="btn btn-secondary"
          onClick={() => startRun()}
          disabled={isStarting}
        >
          {isStarting ? (
            <>
              <Spinner size={13} /> Re-running…
            </>
          ) : (
            "Re-run"
          )}
        </button>
      </div>

      {/* Summary banner */}
      <div
        style={{
          padding: "10px 14px",
          borderRadius: "var(--radius)",
          marginBottom: 20,
          background: allVerified ? "#dcfce7" : "#fef9c3",
          border: `1px solid ${allVerified ? "#16a34a" : "#d97706"}`,
          color: allVerified ? "#15803d" : "#92400e",
          fontSize: 13,
          fontWeight: 500,
        }}
      >
        {allVerified
          ? "✓ All environment checks passed."
          : `${envResult.checks.filter((c) => c.status !== "verified").length} check(s) need attention.`}
      </div>

      {/* Check list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {envResult.checks.map((check) => (
          <div
            key={check.check_id}
            style={{
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              overflow: "hidden",
            }}
          >
            {/* Header row */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 14px",
                background: "var(--surface)",
                cursor: "pointer",
              }}
              onClick={() =>
                setExpandedStep(expandedStep === check.check_id ? null : check.check_id)
              }
            >
              <span
                style={{
                  color: STATUS_COLOR[check.status],
                  fontWeight: 700,
                  fontSize: 16,
                  width: 20,
                }}
              >
                {STATUS_ICON[check.status]}
              </span>
              <span className="mono" style={{ flex: 1 }}>
                {check.command}
              </span>
              <span style={{ color: "var(--muted)", fontSize: 12 }}>
                #{check.step_index}
              </span>
              {check.status === "failed" && (
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: 12, padding: "3px 10px" }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setFixStepId(check.check_id);
                  }}
                >
                  Apply Fix
                </button>
              )}
            </div>

            {/* Expanded output */}
            {expandedStep === check.check_id && (
              <div style={{ padding: "10px 14px", background: "var(--bg)" }}>
                {check.stdout && (
                  <div style={{ marginBottom: 8 }}>
                    <p
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        marginBottom: 4,
                        color: "var(--muted)",
                      }}
                    >
                      stdout
                    </p>
                    <pre
                      className="mono"
                      style={{
                        background: "#f1f5f9",
                        padding: "8px 10px",
                        borderRadius: "var(--radius)",
                        overflowX: "auto",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {check.stdout}
                    </pre>
                  </div>
                )}
                {check.stderr && (
                  <div>
                    <p
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        marginBottom: 4,
                        color: "var(--danger)",
                      }}
                    >
                      stderr
                    </p>
                    <pre
                      className="mono"
                      style={{
                        background: "#fff1f2",
                        padding: "8px 10px",
                        borderRadius: "var(--radius)",
                        overflowX: "auto",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {check.stderr}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Bob diagnosis */}
      {envResult.diagnosis && (
        <div
          className="card"
          style={{ marginTop: 20, borderLeft: "3px solid var(--secondary)" }}
        >
          <h3 style={{ marginBottom: 8 }}>
            Bob Diagnosis{" "}
            <span
              style={{
                fontSize: 11,
                color: "var(--muted)",
                fontWeight: 400,
              }}
            >
              (confidence: {envResult.diagnosis.confidence})
            </span>
          </h3>
          <p style={{ marginBottom: 6 }}>
            <strong>Root cause:</strong> {envResult.diagnosis.root_cause}
          </p>
          <p style={{ marginBottom: 6 }}>
            <strong>Proposed fix:</strong> {envResult.diagnosis.proposed_fix}
          </p>
          {envResult.diagnosis.references.length > 0 && (
            <p style={{ fontSize: 12, color: "var(--muted)" }}>
              References: {envResult.diagnosis.references.join(", ")}
            </p>
          )}
        </div>
      )}

      {/* Approval modal for fix */}
      {fixStepId && (
        <ApprovalModal
          title="Apply Fix"
          message={`Apply the recommended fix for step "${
            envResult.checks.find((c) => c.check_id === fixStepId)?.command ?? fixStepId
          }"? This will re-run the environment check inside the sandbox.`}
          confirmLabel="Apply Fix"
          onConfirm={() => applyFix(fixStepId)}
          onCancel={() => setFixStepId(null)}
          isLoading={isApplying}
        />
      )}
    </div>
  );
}
