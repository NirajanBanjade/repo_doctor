import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTestResults } from "@/api/client";
import Spinner from "@/components/Spinner";
const COMPONENT_STATUS_COLOR = {
    covered_passed: "var(--success)",
    covered_failed: "var(--danger)",
    unexecuted: "var(--muted)",
    no_suitable_test: "var(--warning)",
};
const TEST_STATUS_COLOR = {
    passed: "var(--success)",
    failed: "var(--danger)",
    error: "var(--secondary)",
    skipped: "var(--muted)",
};
export default function TestResultsView({ sessionId }) {
    const [selectedComponent, setSelectedComponent] = useState(null);
    const [expandedTest, setExpandedTest] = useState(null);
    const { data: result, isPending, error, } = useQuery({
        queryKey: ["testresults", sessionId],
        queryFn: () => getTestResults(sessionId),
        retry: false,
    });
    if (isPending) {
        return (_jsxs("div", { style: { display: "flex", gap: 10, alignItems: "center", padding: 32 }, children: [_jsx(Spinner, {}), " Loading test results\u2026"] }));
    }
    if (error || !result) {
        return (_jsx("div", { style: { padding: 32, color: "var(--muted)" }, children: "No test results yet. Approve and run a test plan first." }));
    }
    const filteredTests = selectedComponent
        ? result.test_results.filter((t) => t.linked_node_ids.includes(selectedComponent))
        : result.test_results;
    const passed = result.test_results.filter((t) => t.status === "passed").length;
    const failed = result.test_results.filter((t) => t.status === "failed").length;
    const total = result.test_results.length;
    return (_jsxs("div", { style: { padding: 24 }, children: [_jsx("h2", { style: { marginBottom: 16 }, children: "Test Results" }), result.infrastructure_error && (_jsxs("div", { style: {
                    padding: "10px 14px",
                    marginBottom: 16,
                    background: "#fff1f2",
                    border: "1px solid #fca5a5",
                    borderRadius: "var(--radius)",
                    fontSize: 13,
                    color: "var(--danger)",
                }, children: [_jsx("strong", { children: "Infrastructure error:" }), " ", result.infrastructure_error] })), _jsxs("div", { style: {
                    display: "flex",
                    gap: 16,
                    marginBottom: 20,
                    padding: "10px 16px",
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    fontSize: 13,
                }, children: [_jsxs("span", { style: { color: "var(--success)", fontWeight: 600 }, children: ["\u2713 ", passed, " passed"] }), _jsxs("span", { style: { color: "var(--danger)", fontWeight: 600 }, children: ["\u2717 ", failed, " failed"] }), _jsxs("span", { className: "text-muted", children: [total, " total"] }), _jsxs("span", { className: "text-muted", children: ["exit code: ", result.sandbox_exit_code] })] }), _jsxs("div", { style: { display: "flex", gap: 16 }, children: [_jsxs("div", { style: {
                            width: 240,
                            flexShrink: 0,
                            display: "flex",
                            flexDirection: "column",
                            gap: 6,
                        }, children: [_jsx("p", { style: { fontSize: 12, fontWeight: 600, marginBottom: 4 }, children: "Components" }), _jsx("button", { className: `btn ${selectedComponent === null ? "btn-primary" : "btn-secondary"}`, style: { justifyContent: "flex-start", fontSize: 12, padding: "5px 10px" }, onClick: () => setSelectedComponent(null), children: "All tests" }), result.component_statuses.map((cs) => (_jsxs("button", { className: `btn ${selectedComponent === cs.node_id ? "btn-primary" : "btn-secondary"}`, style: {
                                    justifyContent: "flex-start",
                                    fontSize: 11,
                                    padding: "5px 10px",
                                    gap: 6,
                                }, onClick: () => setSelectedComponent(cs.node_id), children: [_jsx("span", { style: {
                                            width: 8,
                                            height: 8,
                                            borderRadius: "50%",
                                            background: COMPONENT_STATUS_COLOR[cs.status],
                                            flexShrink: 0,
                                            display: "inline-block",
                                        } }), _jsx("span", { className: "mono", style: {
                                            overflow: "hidden",
                                            textOverflow: "ellipsis",
                                            whiteSpace: "nowrap",
                                        }, children: cs.node_id.split("::").pop() }), _jsxs("span", { className: "text-muted", style: { marginLeft: "auto" }, children: [cs.passed, "/", cs.test_count] })] }, cs.node_id)))] }), _jsx("div", { style: { flex: 1, display: "flex", flexDirection: "column", gap: 6 }, children: filteredTests.length === 0 ? (_jsx("p", { className: "text-muted", style: { padding: 12 }, children: "No tests for this component." })) : (filteredTests.map((t) => (_jsxs("div", { style: {
                                border: "1px solid var(--border)",
                                borderRadius: "var(--radius)",
                                overflow: "hidden",
                            }, children: [_jsxs("div", { style: {
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 10,
                                        padding: "8px 12px",
                                        background: "var(--surface)",
                                        cursor: "pointer",
                                    }, onClick: () => setExpandedTest(expandedTest === t.test_id ? null : t.test_id), children: [_jsx("span", { style: {
                                                color: TEST_STATUS_COLOR[t.status],
                                                fontWeight: 700,
                                                width: 16,
                                            }, children: t.status === "passed"
                                                ? "✓"
                                                : t.status === "failed"
                                                    ? "✗"
                                                    : t.status === "skipped"
                                                        ? "—"
                                                        : "!" }), _jsxs("span", { className: "mono", style: { flex: 1, fontSize: 12 }, children: [t.test_file, "::", t.test_function] }), _jsxs("span", { className: "text-muted", style: { fontSize: 11 }, children: [t.duration_ms, "ms"] })] }), expandedTest === t.test_id && (_jsxs("div", { style: { padding: "10px 12px", background: "var(--bg)" }, children: [t.stdout && (_jsx("pre", { className: "mono", style: {
                                                marginBottom: 8,
                                                padding: "6px 8px",
                                                background: "#f1f5f9",
                                                borderRadius: "var(--radius)",
                                                overflowX: "auto",
                                                whiteSpace: "pre-wrap",
                                                fontSize: 11,
                                            }, children: t.stdout })), t.stderr && (_jsx("pre", { className: "mono", style: {
                                                padding: "6px 8px",
                                                background: "#fff1f2",
                                                borderRadius: "var(--radius)",
                                                overflowX: "auto",
                                                whiteSpace: "pre-wrap",
                                                fontSize: 11,
                                                color: "var(--danger)",
                                            }, children: t.stderr }))] }))] }, t.test_id)))) })] })] }));
}
