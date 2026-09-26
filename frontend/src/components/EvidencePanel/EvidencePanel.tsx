import type { CSSProperties } from "react";
import type { EvidenceRef } from "@/types";

const STATUS_STYLE: Record<EvidenceRef["evidence_status"], CSSProperties> = {
  confirmed_static: { color: "var(--success)", fontWeight: 600 },
  observed_test: { color: "var(--accent)", fontWeight: 600 },
  inferred: { color: "var(--warning)", fontWeight: 600 },
};

const STATUS_LABEL: Record<EvidenceRef["evidence_status"], string> = {
  confirmed_static: "static",
  observed_test: "test",
  inferred: "inferred",
};

interface EvidencePanelProps {
  refs: EvidenceRef[];
  onClose?: () => void;
}

export default function EvidencePanel({ refs, onClose }: EvidencePanelProps) {
  return (
    <aside
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: 16,
        minWidth: 280,
        maxWidth: 360,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 10,
        }}
      >
        <h3 style={{ margin: 0 }}>Evidence</h3>
        {onClose && (
          <button
            className="btn btn-secondary"
            onClick={onClose}
            style={{ padding: "2px 8px", fontSize: 12 }}
          >
            ✕
          </button>
        )}
      </div>

      {refs.length === 0 ? (
        <p className="text-muted" style={{ fontSize: 12 }}>
          No evidence references.
        </p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {refs.map((ref, i) => (
            <li
              key={i}
              style={{
                marginBottom: 10,
                paddingBottom: 10,
                borderBottom:
                  i < refs.length - 1
                    ? "1px solid var(--border)"
                    : "none",
              }}
            >
              <div
                className="mono"
                style={{ display: "flex", gap: 6, alignItems: "baseline" }}
              >
                <span style={{ color: "var(--text)" }}>
                  {ref.file}:{ref.line}
                </span>
                <span style={STATUS_STYLE[ref.evidence_status]}>
                  [{STATUS_LABEL[ref.evidence_status]}]
                </span>
              </div>
              {ref.snippet && (
                <pre
                  className="mono"
                  style={{
                    marginTop: 4,
                    padding: "6px 8px",
                    background: "var(--bg)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    overflowX: "auto",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-all",
                  }}
                >
                  {ref.snippet}
                </pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
