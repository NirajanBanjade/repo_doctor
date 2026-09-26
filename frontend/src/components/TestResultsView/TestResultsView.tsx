import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTestResults } from "@/api/client";
import Spinner from "@/components/Spinner";
import type { TestCaseResult, ComponentTestStatus } from "@/types";

const COMPONENT_STATUS_COLOR: Record<
  ComponentTestStatus["status"],
  string
> = {
  covered_passed: "var(--success)",
  covered_failed: "var(--danger)",
  unexecuted: "var(--muted)",
  no_suitable_test: "var(--warning)",
};

const TEST_STATUS_COLOR: Record<TestCaseResult["status"], string> = {
  passed: "var(--success)",
  failed: "var(--danger)",
  error: "var(--secondary)",
  skipped: "var(--muted)",
};

interface Props {
  sessionId: string;
}

export default function TestResultsView({ sessionId }: Props) {
  const [selectedComponent, setSelectedComponent] = useState<string | null>(
    null,
  );
  const [expandedTest, setExpandedTest] = useState<string | null>(null);

  const { data: result, isPending, error } = useQuery({
    queryKey: ["testresults", sessionId],
    queryFn: () => getTestResults(sessionId),
  });

  if (isPending) {
    return (
      <div style={{ display: "flex", gap: 10, alignItems: "center", padding: 32 }}>
        <Spinner /> Loading test results…
      </div>
    );
  }

  if (error || !result) {
    return (
      <div style={{ padding: 32, color: "var(--muted)" }}>
        No test results yet. Approve and run a test plan first.
      </div>
    );
  }

  const filteredTests = selectedComponent
    ? result.test_results.filter((t) =>
        t.linked_node_ids.includes(selectedComponent),
      )
    : result.test_results;

  const passed = result.test_results.filter((t) => t.status === "passed").length;
  const failed = result.test_results.filter((t) => t.status === "failed").length;
  const total = result.test_results.length;

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 16 }}>Test Results</h2>

      {/* Infrastructure error */}
      {result.infrastructure_error && (
        <div
          style={{
            padding: "10px 14px",
            marginBottom: 16,
            background: "#fff1f2",
            border: "1px solid #fca5a5",
            borderRadius: "var(--radius)",
            fontSize: 13,
            color: "var(--danger)",
          }}
        >
          <strong>Infrastructure error:</strong> {result.infrastructure_error}
        </div>
      )}

      {/* Summary bar */}
      <div
        style={{
          display: "flex",
          gap: 16,
          marginBottom: 20,
          padding: "10px 16px",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius)",
          fontSize: 13,
        }}
      >
        <span style={{ color: "var(--success)", fontWeight: 600 }}>
          ✓ {passed} passed
        </span>
        <span style={{ color: "var(--danger)", fontWeight: 600 }}>
          ✗ {failed} failed
        </span>
        <span className="text-muted">{total} total</span>
        <span className="text-muted">
          exit code: {result.sandbox_exit_code}
        </span>
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        {/* Component status sidebar */}
        <div
          style={{
            width: 240,
            flexShrink: 0,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Components
          </p>
          <button
            className={`btn ${selectedComponent === null ? "btn-primary" : "btn-secondary"}`}
            style={{ justifyContent: "flex-start", fontSize: 12, padding: "5px 10px" }}
            onClick={() => setSelectedComponent(null)}
          >
            All tests
          </button>
          {result.component_statuses.map((cs) => (
            <button
              key={cs.node_id}
              className={`btn ${selectedComponent === cs.node_id ? "btn-primary" : "btn-secondary"}`}
              style={{ justifyContent: "flex-start", fontSize: 11, padding: "5px 10px", gap: 6 }}
              onClick={() => setSelectedComponent(cs.node_id)}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: COMPONENT_STATUS_COLOR[cs.status],
                  flexShrink: 0,
                  display: "inline-block",
                }}
              />
              <span
                className="mono"
                style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
              >
                {cs.node_id.split("::").pop()}
              </span>
              <span className="text-muted" style={{ marginLeft: "auto" }}>
                {cs.passed}/{cs.test_count}
              </span>
            </button>
          ))}
        </div>

        {/* Test case list */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
          {filteredTests.length === 0 ? (
            <p className="text-muted" style={{ padding: 12 }}>
              No tests for this component.
            </p>
          ) : (
            filteredTests.map((t) => (
              <div
                key={t.test_id}
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "8px 12px",
                    background: "var(--surface)",
                    cursor: "pointer",
                  }}
                  onClick={() =>
                    setExpandedTest(
                      expandedTest === t.test_id ? null : t.test_id,
                    )
                  }
                >
                  <span
                    style={{
                      color: TEST_STATUS_COLOR[t.status],
                      fontWeight: 700,
                      width: 16,
                    }}
                  >
                    {t.status === "passed"
                      ? "✓"
                      : t.status === "failed"
                        ? "✗"
                        : t.status === "skipped"
                          ? "—"
                          : "!"}
                  </span>
                  <span className="mono" style={{ flex: 1, fontSize: 12 }}>
                    {t.test_file}::{t.test_function}
                  </span>
                  <span className="text-muted" style={{ fontSize: 11 }}>
                    {t.duration_ms}ms
                  </span>
                </div>

                {expandedTest === t.test_id && (
                  <div style={{ padding: "10px 12px", background: "var(--bg)" }}>
                    {t.stdout && (
                      <pre
                        className="mono"
                        style={{
                          marginBottom: 8,
                          padding: "6px 8px",
                          background: "#f1f5f9",
                          borderRadius: "var(--radius)",
                          overflowX: "auto",
                          whiteSpace: "pre-wrap",
                          fontSize: 11,
                        }}
                      >
                        {t.stdout}
                      </pre>
                    )}
                    {t.stderr && (
                      <pre
                        className="mono"
                        style={{
                          padding: "6px 8px",
                          background: "#fff1f2",
                          borderRadius: "var(--radius)",
                          overflowX: "auto",
                          whiteSpace: "pre-wrap",
                          fontSize: 11,
                          color: "var(--danger)",
                        }}
                      >
                        {t.stderr}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
