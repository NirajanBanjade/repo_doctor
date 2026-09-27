import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getTestPlan, approveTestPlan, runTests, refinePlan } from "@/api/client";
import ApprovalModal from "@/components/ApprovalModal";
import Spinner from "@/components/Spinner";
const COVERAGE_COLOR = {
    covered: "var(--success)",
    indirect: "var(--warning)",
    none: "var(--danger)",
};
export default function TestPlanView({ sessionId, onRan }) {
    const qc = useQueryClient();
    const [showApproval, setShowApproval] = useState(false);
    const [feedback, setFeedback] = useState("");
    const [expandedScenario, setExpandedScenario] = useState(null);
    const { data: plan, isPending, error, } = useQuery({
        queryKey: ["testplan", sessionId],
        queryFn: () => getTestPlan(sessionId),
        retry: false,
    });
    const { mutate: approve, isPending: isApproving } = useMutation({
        mutationFn: () => approveTestPlan(sessionId, { plan_id: plan.plan_id, approved: true }),
        onSuccess: (updatedPlan) => {
            setShowApproval(false);
            qc.setQueryData(["testplan", sessionId], updatedPlan);
        },
    });
    const { mutate: runAll, isPending: isRunning } = useMutation({
        mutationFn: () => runTests(sessionId, plan.plan_id),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["testresults", sessionId] });
            void qc.invalidateQueries({ queryKey: ["verification", sessionId] });
            onRan?.();
        },
    });
    const { mutate: refine, isPending: isRefining } = useMutation({
        mutationFn: () => refinePlan(sessionId, plan.plan_id, feedback),
        onSuccess: (updated) => {
            qc.setQueryData(["testplan", sessionId], updated);
            setFeedback("");
        },
    });
    if (isPending) {
        return (_jsxs("div", { style: { display: "flex", gap: 10, alignItems: "center", padding: 32 }, children: [_jsx(Spinner, {}), " Loading test plan\u2026"] }));
    }
    if (error || !plan) {
        return (_jsx("div", { style: { padding: 32, color: "var(--muted)" }, children: "No test plan yet. Run Impact Scope, choose feature files, and create a plan." }));
    }
    const isPlanApproved = plan.status === "approved";
    const isPlanProposed = plan.status === "proposed";
    return (_jsxs("div", { style: { padding: 24, maxWidth: 820 }, children: [_jsxs("div", { style: {
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 20,
                }, children: [_jsxs("div", { children: [_jsx("h2", { style: { marginBottom: 4 }, children: "Test Plan" }), _jsx("p", { style: { fontSize: 13, color: "var(--muted)", margin: 0 }, children: "Bob analysed the selected files and proposed the scenarios below. Review them, refine if needed, then approve to generate test files." })] }), _jsxs("div", { style: { display: "flex", gap: 8, flexShrink: 0, marginLeft: 16 }, children: [isPlanProposed && (_jsx("button", { className: "btn btn-primary", onClick: () => setShowApproval(true), children: "Approve & Generate Tests" })), isPlanApproved && (_jsx("button", { className: "btn btn-primary", onClick: () => runAll(), disabled: isRunning, children: isRunning ? (_jsxs(_Fragment, { children: [_jsx(Spinner, { size: 13 }), " Running tests\u2026"] })) : ("Run Tests") }))] })] }), _jsx("div", { style: { marginBottom: 20 }, children: _jsx("span", { style: {
                        padding: "3px 12px",
                        borderRadius: 12,
                        fontSize: 12,
                        fontWeight: 600,
                        background: plan.status === "approved"
                            ? "#dcfce7"
                            : plan.status === "rejected"
                                ? "#fee2e2"
                                : "#eff6ff",
                        color: plan.status === "approved"
                            ? "var(--success)"
                            : plan.status === "rejected"
                                ? "var(--danger)"
                                : "var(--accent)",
                        border: "1px solid transparent",
                    }, children: plan.status.toUpperCase() }) }), isPlanApproved && (_jsxs("div", { style: {
                    marginBottom: 20,
                    padding: "12px 16px",
                    background: plan.generated_files.length > 0 ? "#f0fdf4" : "#fff1f2",
                    border: `1px solid ${plan.generated_files.length > 0 ? "#86efac" : "#fca5a5"}`,
                    borderRadius: "var(--radius)",
                    fontSize: 13,
                }, children: [_jsx("strong", { children: plan.generated_files.length > 0
                            ? `${plan.generated_files.length} test file(s) generated`
                            : "Test generation failed" }), plan.generated_files.map((file) => (_jsx("p", { className: "mono", style: { fontSize: 11, marginTop: 5 }, children: file }, file)))] })), plan.overall_rationale && (_jsxs("div", { style: {
                    marginBottom: 20,
                    padding: "12px 16px",
                    background: "#eff6ff",
                    border: "1px solid #bfdbfe",
                    borderRadius: "var(--radius)",
                    fontSize: 13,
                    lineHeight: 1.6,
                }, children: [_jsx("p", { style: { fontWeight: 600, marginBottom: 4, color: "var(--accent)" }, children: "Bob's analysis" }), _jsx("p", { style: { margin: 0, color: "var(--text)" }, children: plan.overall_rationale })] })), plan.analysis_notes.length > 0 && (_jsxs("div", { style: {
                    marginBottom: 20,
                    padding: "10px 14px",
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                }, children: [_jsx("p", { style: { fontWeight: 600, fontSize: 12, marginBottom: 6 }, children: "Notes" }), _jsx("ul", { style: { margin: 0, paddingLeft: 18 }, children: plan.analysis_notes.map((note, i) => (_jsx("li", { style: { fontSize: 12, color: "var(--muted)", marginBottom: 3 }, children: note }, i))) })] })), plan.coverage_gaps.length > 0 && (_jsxs("div", { style: {
                    marginBottom: 20,
                    padding: "10px 14px",
                    background: "#fff1f2",
                    border: "1px solid #fca5a5",
                    borderRadius: "var(--radius)",
                    fontSize: 13,
                }, children: [_jsx("strong", { children: "Coverage gaps" }), " \u2014 ", plan.coverage_gaps.length, " node(s) have no existing test:", _jsx("ul", { style: { margin: "6px 0 0 18px" }, children: plan.coverage_gaps.map((n) => (_jsx("li", { className: "mono", style: { fontSize: 12 }, children: n }, n))) })] })), _jsxs("h3", { style: { marginBottom: 12 }, children: ["Proposed Test Scenarios (", plan.scenarios.length, ")"] }), _jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 10, marginBottom: 28 }, children: [plan.scenarios.length === 0 && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: "No scenarios yet \u2014 Bob could not generate a plan (Bob unavailable). You can still approve an empty plan or add feedback below to retry." })), plan.scenarios.map((scenario, idx) => {
                        const isOpen = expandedScenario === scenario.scenario_id;
                        return (_jsxs("div", { style: {
                                border: "1px solid var(--border)",
                                borderRadius: "var(--radius)",
                                overflow: "hidden",
                                background: "var(--bg)",
                            }, children: [_jsxs("div", { style: {
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "flex-start",
                                        padding: "12px 14px",
                                        cursor: "pointer",
                                        background: isOpen ? "var(--surface)" : "var(--bg)",
                                    }, onClick: () => setExpandedScenario(isOpen ? null : (scenario.scenario_id ?? String(idx))), children: [_jsxs("div", { style: { flex: 1, minWidth: 0 }, children: [_jsxs("p", { style: { fontWeight: 600, fontSize: 13, marginBottom: 4 }, children: [idx + 1, ". ", scenario.name] }), _jsx("p", { style: { fontSize: 12, color: "var(--muted)", margin: 0 }, children: scenario.expected_behavior })] }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center", flexShrink: 0, marginLeft: 12 }, children: [_jsx("span", { className: "mono", style: { fontSize: 11, color: "var(--muted)" }, children: scenario.proposed_test_function }), _jsx("span", { style: { fontSize: 12, color: "var(--muted)" }, children: isOpen ? "▲" : "▼" })] })] }), isOpen && (_jsxs("div", { style: {
                                        padding: "12px 14px",
                                        borderTop: "1px solid var(--border)",
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: 10,
                                    }, children: [scenario.rationale && (_jsxs("div", { children: [_jsx("p", { style: { fontSize: 11, fontWeight: 600, color: "var(--accent)", marginBottom: 3 }, children: "Why this test matters" }), _jsx("p", { style: { fontSize: 12, color: "var(--text)", margin: 0 }, children: scenario.rationale })] })), scenario.edge_cases.length > 0 && (_jsxs("div", { children: [_jsx("p", { style: { fontSize: 11, fontWeight: 600, color: "var(--secondary)", marginBottom: 3 }, children: "Edge cases Bob will cover" }), _jsx("ul", { style: { margin: 0, paddingLeft: 18 }, children: scenario.edge_cases.map((ec, i) => (_jsx("li", { style: { fontSize: 12, color: "var(--text)", marginBottom: 2 }, children: ec }, i))) })] })), _jsxs("div", { style: { display: "flex", gap: 16, flexWrap: "wrap" }, children: [_jsxs("div", { children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", marginBottom: 2 }, children: "Component" }), _jsx("p", { className: "mono", style: { fontSize: 11 }, children: scenario.component_id })] }), _jsxs("div", { children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", marginBottom: 2 }, children: "Test file" }), _jsx("p", { className: "mono", style: { fontSize: 11 }, children: scenario.proposed_test_file })] }), _jsxs("div", { children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", marginBottom: 2 }, children: "Evidence" }), _jsx("p", { className: "mono", style: { fontSize: 11 }, children: scenario.source_evidence })] }), scenario.generation_status && (_jsxs("div", { children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", marginBottom: 2 }, children: "Generation" }), _jsx("p", { style: { fontSize: 11 }, children: scenario.generation_status })] }))] })] }))] }, scenario.scenario_id ?? idx));
                    })] }), plan.existing_test_mappings.length > 0 && (_jsxs("div", { style: { marginBottom: 24 }, children: [_jsx("h3", { style: { marginBottom: 8 }, children: "Existing Test Coverage" }), _jsx("div", { style: { display: "flex", flexDirection: "column", gap: 6 }, children: plan.existing_test_mappings.map((m) => (_jsxs("div", { style: {
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
                                    }, children: m.coverage_status }), _jsxs("div", { children: [_jsx("p", { className: "mono", style: { fontSize: 12, marginBottom: 2 }, children: m.node_id }), m.test_files.map((f) => (_jsx("p", { style: { fontSize: 11, color: "var(--muted)" }, children: f }, f)))] })] }, m.node_id))) })] })), isPlanProposed && (_jsxs("div", { style: {
                    marginBottom: 24,
                    padding: "16px",
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                }, children: [_jsx("p", { style: { fontWeight: 600, fontSize: 13, marginBottom: 6 }, children: "Ask Bob to refine the plan" }), _jsx("p", { style: { fontSize: 12, color: "var(--muted)", marginBottom: 10 }, children: "Tell Bob what to add, remove, or change \u2014 e.g. \"add edge cases for null inputs\", \"focus only on the payment module\", \"add a scenario for the error path in submit_order\"." }), _jsx("textarea", { value: feedback, onChange: (e) => setFeedback(e.target.value), placeholder: "Your feedback to Bob\u2026", rows: 3, style: { width: "100%", marginBottom: 8, resize: "vertical", boxSizing: "border-box" } }), _jsx("button", { className: "btn btn-secondary", disabled: isRefining || !feedback.trim(), onClick: () => refine(), children: isRefining ? (_jsxs(_Fragment, { children: [_jsx(Spinner, { size: 13 }), " Refining\u2026"] })) : ("Refine Plan") })] })), (plan.external_feature_suggestions?.length ?? 0) > 0 && (_jsxs("div", { style: {
                    marginBottom: 20,
                    padding: 12,
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                }, children: [_jsx("strong", { children: "Optional cross-feature regression tests" }), _jsx("p", { className: "text-muted", style: { fontSize: 12, margin: "4px 0 8px" }, children: "These connected features are outside the primary plan and were not added automatically." }), plan.external_feature_suggestions.map((feature) => (_jsxs("div", { style: { fontSize: 12 }, children: [feature.name, " \u2014 ", feature.reason] }, feature.feature_id)))] })), showApproval && (_jsx(ApprovalModal, { title: "Approve Test Plan", message: `Approving this plan will generate ${plan.scenarios.length} test file(s) in the working copy. The original repository will not be modified, and the tests will not run until you click Run Tests.`, confirmLabel: "Approve & Generate", onConfirm: () => approve(), onCancel: () => setShowApproval(false), isLoading: isApproving }))] }));
}
