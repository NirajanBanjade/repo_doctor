import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getVerificationReport } from "@/api/client";
import EvidencePanel from "@/components/EvidencePanel";
import Spinner from "@/components/Spinner";
import type { ComponentVerification, DocumentationGap } from "@/types";

const COMP_STATUS_COLOR: Record<ComponentVerification["status"], string> = {
  passed: "var(--success)",
  failed: "var(--danger)",
  unexecuted: "var(--muted)",
  no_test: "var(--warning)",
};

interface Props {
  sessionId: string;
}

export default function VerificationView({ sessionId }: Props) {
  const [selectedComp, setSelectedComp] = useState<string | null>(null);
  const [showPrSummary, setShowPrSummary] = useState(false);

  const {
    data: report,
    isPending,
    error,
  } = useQuery({
    queryKey: ["verification", sessionId],
    queryFn: () => getVerificationReport(sessionId),
    retry: false,
  });

  if (isPending) {
    return (
      <div style={{ display: "flex", gap: 10, alignItems: "center", padding: 32 }}>
        <Spinner /> Loading verification report…
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ padding: 32, color: "var(--muted)" }}>
        No verification report yet. Run tests to generate one.
      </div>
    );
  }

  const selectedEv =
    report.components_verified.find((c) => c.component_id === selectedComp)
      ?.evidence_refs ?? [];

  return (
    <div style={{ padding: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
        }}
      >
        <h2>Verification Report</h2>
        <button className="btn btn-primary" onClick={() => setShowPrSummary(true)}>
          View PR Summary
        </button>
      </div>

      {/* Components verified */}
      <section style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 10 }}>Components Verified</h3>
        <div style={{ display: "flex", gap: 16 }}>
          <div
            style={{
              width: 240,
              display: "flex",
              flexDirection: "column",
              gap: 5,
            }}
          >
            {report.components_verified.map((cv) => (
              <button
                key={cv.component_id}
                className={`btn ${selectedComp === cv.component_id ? "btn-primary" : "btn-secondary"}`}
                style={{
                  justifyContent: "flex-start",
                  fontSize: 11,
                  padding: "5px 10px",
                  gap: 8,
                }}
                onClick={() =>
                  setSelectedComp(
                    selectedComp === cv.component_id ? null : cv.component_id,
                  )
                }
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: COMP_STATUS_COLOR[cv.status],
                    flexShrink: 0,
                    display: "inline-block",
                  }}
                />
                <span
                  className="mono"
                  style={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    flex: 1,
                  }}
                >
                  {cv.component_id.split("::").pop()}
                </span>
                <span
                  style={{
                    fontSize: 10,
                    color: COMP_STATUS_COLOR[cv.status],
                    fontWeight: 600,
                  }}
                >
                  {cv.status}
                </span>
              </button>
            ))}
          </div>

          {selectedComp && (
            <EvidencePanel refs={selectedEv} onClose={() => setSelectedComp(null)} />
          )}
        </div>
      </section>

      {/* Unresolved risks */}
      {report.unresolved_risks.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 10 }}>
            Unresolved Risks ({report.unresolved_risks.length})
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {report.unresolved_risks.map((risk, i) => (
              <div
                key={i}
                style={{
                  padding: "10px 14px",
                  background: "#fef9c3",
                  border: "1px solid #d97706",
                  borderRadius: "var(--radius)",
                  fontSize: 13,
                }}
              >
                <p style={{ fontWeight: 600, marginBottom: 4 }}>⚠ {risk.hypothesis}</p>
                <p className="text-muted" style={{ fontSize: 12 }}>
                  Component: <span className="mono">{risk.component_id}</span>
                </p>
                <p className="text-muted" style={{ fontSize: 12 }}>
                  {risk.reason_unresolved}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Documentation gaps */}
      {report.documentation_gaps.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 10 }}>
            Documentation Gaps ({report.documentation_gaps.length})
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {report.documentation_gaps.map((gap: DocumentationGap, i) => (
              <div
                key={i}
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    padding: "8px 12px",
                    background: "var(--surface)",
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span className="mono" style={{ fontSize: 12 }}>
                    {gap.file}
                  </span>
                  <span className="text-muted" style={{ fontSize: 12 }}>
                    {gap.reason}
                  </span>
                </div>
                <div style={{ display: "flex" }}>
                  <pre
                    className="mono"
                    style={{
                      flex: 1,
                      padding: "8px 10px",
                      background: "#fff1f2",
                      fontSize: 11,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-all",
                      borderRight: "1px solid var(--border)",
                    }}
                  >
                    {gap.current_text}
                  </pre>
                  <pre
                    className="mono"
                    style={{
                      flex: 1,
                      padding: "8px 10px",
                      background: "#f0fdf4",
                      fontSize: 11,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-all",
                    }}
                  >
                    {gap.proposed_text}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* PR Summary modal */}
      {showPrSummary && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowPrSummary(false)}
        >
          <div
            style={{
              background: "var(--bg)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              padding: 24,
              maxWidth: 680,
              width: "100%",
              maxHeight: "80vh",
              overflowY: "auto",
              boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 16,
              }}
            >
              <h2>PR Summary</h2>
              <button
                className="btn btn-secondary"
                style={{ padding: "3px 10px" }}
                onClick={() => setShowPrSummary(false)}
              >
                ✕
              </button>
            </div>
            <pre
              style={{
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontSize: 13,
                lineHeight: 1.7,
                fontFamily: "inherit",
              }}
            >
              {report.pr_summary}
            </pre>
            <p className="text-muted" style={{ fontSize: 11, marginTop: 12 }}>
              Generated at {new Date(report.generated_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
