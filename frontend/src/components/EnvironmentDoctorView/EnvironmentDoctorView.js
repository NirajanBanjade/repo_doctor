import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { runEnvironment, getEnvironmentStatus, applyEnvironmentFix, } from "@/api/client";
import Spinner from "@/components/Spinner";
import ApprovalModal from "@/components/ApprovalModal";
const STATUS_ICON = {
    verified: "✓",
    failed: "✗",
    blocked: "⚠",
    infrastructure_error: "⚡",
};
const STATUS_COLOR = {
    verified: "var(--success)",
    failed: "var(--danger)",
    blocked: "var(--warning)",
    infrastructure_error: "var(--secondary)",
};
export default function EnvironmentDoctorView({ sessionId }) {
    const qc = useQueryClient();
    const [fixStepId, setFixStepId] = useState(null);
    const [expandedStep, setExpandedStep] = useState(null);
    const { data: envResult, isPending, error, } = useQuery({
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
        mutationFn: (stepId) => applyEnvironmentFix(sessionId, {
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
        return (_jsxs("div", { style: { display: "flex", gap: 10, alignItems: "center", padding: 32 }, children: [_jsx(Spinner, {}), " Loading environment status\u2026"] }));
    }
    if (error || !envResult || envResult.checks.length === 0) {
        return (_jsxs("div", { style: { padding: 32 }, children: [_jsx("p", { className: "text-muted", style: { marginBottom: 12 }, children: "No environment run yet. Start the Environment Doctor to verify your setup." }), _jsx("button", { className: "btn btn-primary", onClick: () => startRun(), disabled: isStarting, children: isStarting ? (_jsxs(_Fragment, { children: [_jsx(Spinner, { size: 14 }), " Running\u2026"] })) : ("Run Environment Doctor") })] }));
    }
    const allVerified = envResult.all_verified;
    return (_jsxs("div", { style: { padding: 24 }, children: [_jsxs("div", { style: {
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 16,
                }, children: [_jsx("h2", { children: "Environment Doctor" }), _jsx("button", { className: "btn btn-secondary", onClick: () => startRun(), disabled: isStarting, children: isStarting ? (_jsxs(_Fragment, { children: [_jsx(Spinner, { size: 13 }), " Re-running\u2026"] })) : ("Re-run") })] }), _jsx("div", { style: {
                    padding: "10px 14px",
                    borderRadius: "var(--radius)",
                    marginBottom: 20,
                    background: allVerified ? "#dcfce7" : "#fef9c3",
                    border: `1px solid ${allVerified ? "#16a34a" : "#d97706"}`,
                    color: allVerified ? "#15803d" : "#92400e",
                    fontSize: 13,
                    fontWeight: 500,
                }, children: allVerified
                    ? "✓ All environment checks passed."
                    : `${envResult.checks.filter((c) => c.status !== "verified").length} check(s) need attention.` }), _jsx("div", { style: { display: "flex", flexDirection: "column", gap: 8 }, children: envResult.checks.map((check) => (_jsxs("div", { style: {
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius)",
                        overflow: "hidden",
                    }, children: [_jsxs("div", { style: {
                                display: "flex",
                                alignItems: "center",
                                gap: 10,
                                padding: "10px 14px",
                                background: "var(--surface)",
                                cursor: "pointer",
                            }, onClick: () => setExpandedStep(expandedStep === check.check_id ? null : check.check_id), children: [_jsx("span", { style: {
                                        color: STATUS_COLOR[check.status],
                                        fontWeight: 700,
                                        fontSize: 16,
                                        width: 20,
                                    }, children: STATUS_ICON[check.status] }), _jsx("span", { className: "mono", style: { flex: 1 }, children: check.command }), _jsxs("span", { style: { color: "var(--muted)", fontSize: 12 }, children: ["#", check.step_index] }), check.status === "failed" && (_jsx("button", { className: "btn btn-secondary", style: { fontSize: 12, padding: "3px 10px" }, onClick: (e) => {
                                        e.stopPropagation();
                                        setFixStepId(check.check_id);
                                    }, children: "Apply Fix" }))] }), expandedStep === check.check_id && (_jsxs("div", { style: { padding: "10px 14px", background: "var(--bg)" }, children: [check.stdout && (_jsxs("div", { style: { marginBottom: 8 }, children: [_jsx("p", { style: {
                                                fontSize: 11,
                                                fontWeight: 600,
                                                marginBottom: 4,
                                                color: "var(--muted)",
                                            }, children: "stdout" }), _jsx("pre", { className: "mono", style: {
                                                background: "#f1f5f9",
                                                padding: "8px 10px",
                                                borderRadius: "var(--radius)",
                                                overflowX: "auto",
                                                whiteSpace: "pre-wrap",
                                            }, children: check.stdout })] })), check.stderr && (_jsxs("div", { children: [_jsx("p", { style: {
                                                fontSize: 11,
                                                fontWeight: 600,
                                                marginBottom: 4,
                                                color: "var(--danger)",
                                            }, children: "stderr" }), _jsx("pre", { className: "mono", style: {
                                                background: "#fff1f2",
                                                padding: "8px 10px",
                                                borderRadius: "var(--radius)",
                                                overflowX: "auto",
                                                whiteSpace: "pre-wrap",
                                            }, children: check.stderr })] }))] }))] }, check.check_id))) }), envResult.diagnosis && (_jsxs("div", { className: "card", style: { marginTop: 20, borderLeft: "3px solid var(--secondary)" }, children: [_jsxs("h3", { style: { marginBottom: 8 }, children: ["Bob Diagnosis", " ", _jsxs("span", { style: {
                                    fontSize: 11,
                                    color: "var(--muted)",
                                    fontWeight: 400,
                                }, children: ["(confidence: ", envResult.diagnosis.confidence, ")"] })] }), _jsxs("p", { style: { marginBottom: 6 }, children: [_jsx("strong", { children: "Root cause:" }), " ", envResult.diagnosis.root_cause] }), _jsxs("p", { style: { marginBottom: 6 }, children: [_jsx("strong", { children: "Proposed fix:" }), " ", envResult.diagnosis.proposed_fix] }), envResult.diagnosis.references.length > 0 && (_jsxs("p", { style: { fontSize: 12, color: "var(--muted)" }, children: ["References: ", envResult.diagnosis.references.join(", ")] }))] })), fixStepId && (_jsx(ApprovalModal, { title: "Apply Fix", message: `Apply the recommended fix for step "${envResult.checks.find((c) => c.check_id === fixStepId)?.command ?? fixStepId}"? This will re-run the environment check inside the sandbox.`, confirmLabel: "Apply Fix", onConfirm: () => applyFix(fixStepId), onCancel: () => setFixStepId(null), isLoading: isApplying }))] }));
}
