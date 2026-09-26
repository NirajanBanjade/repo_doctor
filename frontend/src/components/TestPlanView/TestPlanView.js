import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getTestPlan, approveTestPlan, runTests } from "@/api/client";
import ApprovalModal from "@/components/ApprovalModal";
import Spinner from "@/components/Spinner";
const COVERAGE_COLOR = {
    covered: "var(--success)",
    indirect: "var(--warning)",
    none: "var(--danger)",
};
export default function TestPlanView({ sessionId, onApproved }) {
    const qc = useQueryClient();
    const [showApproval, setShowApproval] = useState(false);
    const { data: plan, isPending, error } = useQuery({
        queryKey: ["testplan", sessionId],
        queryFn: () => getTestPlan(sessionId),
    });
    const { mutate: approve, isPending: isApproving } = useMutation({
        mutationFn: () => approveTestPlan(sessionId, { plan_id: plan.plan_id, approved: true }),
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
        return (_jsxs("div", { style: { display: "flex", gap: 10, alignItems: "center", padding: 32 }, children: [_jsx(Spinner, {}), " Loading test plan\u2026"] }));
    }
    if (error || !plan) {
        return (_jsx("div", { style: { padding: 32, color: "var(--muted)" }, children: "No test plan yet. Run an impact analysis first." }));
    }
    const isPlanApproved = plan.status === "approved";
    return (_jsxs("div", { style: { padding: 24 }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }, children: [_jsx("h2", { children: "Test Plan" }), _jsxs("div", { style: { display: "flex", gap: 8 }, children: [!isPlanApproved && (_jsx("button", { className: "btn btn-primary", onClick: () => setShowApproval(true), children: "Approve Plan" })), isPlanApproved && (_jsx("button", { className: "btn btn-primary", onClick: () => runAll(), disabled: isRunning, children: isRunning ? _jsxs(_Fragment, { children: [_jsx(Spinner, { size: 13 }), " Running tests\u2026"] }) : "Run Tests" }))] })] }), _jsx("div", { style: { marginBottom: 16 }, children: _jsx("span", { style: {
                        padding: "3px 12px",
                        borderRadius: 12,
                        fontSize: 12,
                        fontWeight: 600,
                        background: plan.status === "approved"
                            ? "#dcfce7"
                            : plan.status === "rejected"
                                ? "#fee2e2"
                                : "#fef9c3",
                        color: plan.status === "approved"
                            ? "var(--success)"
                            : plan.status === "rejected"
                                ? "var(--danger)"
                                : "var(--warning)",
                        border: "1px solid transparent",
                    }, children: plan.status.toUpperCase() }) }), plan.coverage_gaps.length > 0 && (_jsxs("div", { style: {
                    marginBottom: 20,
                    padding: "10px 14px",
                    background: "#fff1f2",
                    border: "1px solid #fca5a5",
                    borderRadius: "var(--radius)",
                    fontSize: 13,
                }, children: [_jsx("strong", { children: "Coverage gaps" }), " \u2014 ", plan.coverage_gaps.length, " node(s) have no existing test:", _jsx("ul", { style: { margin: "6px 0 0 18px" }, children: plan.coverage_gaps.map((n) => (_jsx("li", { className: "mono", style: { fontSize: 12 }, children: n }, n))) })] })), plan.existing_test_mappings.length > 0 && (_jsxs("div", { style: { marginBottom: 20 }, children: [_jsx("h3", { style: { marginBottom: 8 }, children: "Existing Test Coverage" }), _jsx("div", { style: { display: "flex", flexDirection: "column", gap: 6 }, children: plan.existing_test_mappings.map((m) => (_jsxs("div", { style: {
                                display: "flex",
                                gap: 10,
                                alignItems: "flex-start",
                                padding: "8px 12px",
                                background: "var(--surface)",
                                border: "1px solid var(--border)",
                                borderRadius: "var(--radius)",
                            }, children: [_jsx("span", { style: {
                                        fontSize: 11,
                                        fontWeight: 600,
                                        color: COVERAGE_COLOR[m.coverage_status],
                                        whiteSpace: "nowrap",
                                        padding: "2px 6px",
                                        background: COVERAGE_COLOR[m.coverage_status] + "1a",
                                        borderRadius: 10,
                                        marginTop: 1,
                                    }, children: m.coverage_status }), _jsxs("div", { children: [_jsx("p", { className: "mono", style: { fontSize: 12, marginBottom: 2 }, children: m.node_id }), m.test_files.map((f) => (_jsx("p", { style: { fontSize: 11, color: "var(--muted)" }, children: f }, f)))] })] }, m.node_id))) })] })), _jsxs("h3", { style: { marginBottom: 10 }, children: ["Proposed Scenarios (", plan.scenarios.length, ")"] }), _jsx("div", { style: { display: "flex", flexDirection: "column", gap: 10 }, children: plan.scenarios.map((scenario) => (_jsxs("div", { style: {
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius)",
                        padding: "12px 14px",
                        background: "var(--bg)",
                    }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", marginBottom: 6 }, children: [_jsx("strong", { style: { fontSize: 13 }, children: scenario.name }), _jsx("span", { className: "mono text-muted", style: { fontSize: 11 }, children: scenario.proposed_test_function })] }), _jsx("p", { style: { fontSize: 12, marginBottom: 6, color: "var(--text)" }, children: scenario.expected_behavior }), _jsxs("p", { className: "mono", style: { fontSize: 11, color: "var(--muted)" }, children: [scenario.proposed_test_file, " \u00B7 source: ", scenario.source_evidence] })] }, scenario.scenario_id))) }), showApproval && (_jsx(ApprovalModal, { title: "Approve Test Plan", message: `This will generate ${plan.scenarios.length} test file(s) in the working copy and execute them inside the sandbox. The original repository is never modified. Proceed?`, confirmLabel: "Approve & Continue", onConfirm: () => approve(), onCancel: () => setShowApproval(false), isLoading: isApproving }))] }));
}
