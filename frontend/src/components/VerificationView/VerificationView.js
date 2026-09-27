import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getVerificationReport } from "@/api/client";
import EvidencePanel from "@/components/EvidencePanel";
import Spinner from "@/components/Spinner";
const COMP_STATUS_COLOR = {
    passed: "var(--success)",
    failed: "var(--danger)",
    unexecuted: "var(--muted)",
    no_test: "var(--warning)",
};
export default function VerificationView({ sessionId }) {
    const [selectedComp, setSelectedComp] = useState(null);
    const [showPrSummary, setShowPrSummary] = useState(false);
    const { data: report, isPending, error, } = useQuery({
        queryKey: ["verification", sessionId],
        queryFn: () => getVerificationReport(sessionId),
        retry: false,
    });
    if (isPending) {
        return (_jsxs("div", { style: { display: "flex", gap: 10, alignItems: "center", padding: 32 }, children: [_jsx(Spinner, {}), " Loading verification report\u2026"] }));
    }
    if (error || !report) {
        return (_jsx("div", { style: { padding: 32, color: "var(--muted)" }, children: "No verification report yet. Run tests to generate one." }));
    }
    const selectedEv = report.components_verified.find((c) => c.component_id === selectedComp)
        ?.evidence_refs ?? [];
    return (_jsxs("div", { style: { padding: 24 }, children: [_jsxs("div", { style: {
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 20,
                }, children: [_jsx("h2", { children: "Verification Report" }), _jsx("button", { className: "btn btn-primary", onClick: () => setShowPrSummary(true), children: "View PR Summary" })] }), _jsxs("section", { style: { marginBottom: 24 }, children: [_jsx("h3", { style: { marginBottom: 10 }, children: "Components Verified" }), _jsxs("div", { style: { display: "flex", gap: 16 }, children: [_jsx("div", { style: {
                                    width: 240,
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: 5,
                                }, children: report.components_verified.map((cv) => (_jsxs("button", { className: `btn ${selectedComp === cv.component_id ? "btn-primary" : "btn-secondary"}`, style: {
                                        justifyContent: "flex-start",
                                        fontSize: 11,
                                        padding: "5px 10px",
                                        gap: 8,
                                    }, onClick: () => setSelectedComp(selectedComp === cv.component_id ? null : cv.component_id), children: [_jsx("span", { style: {
                                                width: 8,
                                                height: 8,
                                                borderRadius: "50%",
                                                background: COMP_STATUS_COLOR[cv.status],
                                                flexShrink: 0,
                                                display: "inline-block",
                                            } }), _jsx("span", { className: "mono", style: {
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap",
                                                flex: 1,
                                            }, children: cv.component_id.split("::").pop() }), _jsx("span", { style: {
                                                fontSize: 10,
                                                color: COMP_STATUS_COLOR[cv.status],
                                                fontWeight: 600,
                                            }, children: cv.status })] }, cv.component_id))) }), selectedComp && (_jsx(EvidencePanel, { refs: selectedEv, onClose: () => setSelectedComp(null) }))] })] }), report.unresolved_risks.length > 0 && (_jsxs("section", { style: { marginBottom: 24 }, children: [_jsxs("h3", { style: { marginBottom: 10 }, children: ["Unresolved Risks (", report.unresolved_risks.length, ")"] }), _jsx("div", { style: { display: "flex", flexDirection: "column", gap: 8 }, children: report.unresolved_risks.map((risk, i) => (_jsxs("div", { style: {
                                padding: "10px 14px",
                                background: "#fef9c3",
                                border: "1px solid #d97706",
                                borderRadius: "var(--radius)",
                                fontSize: 13,
                            }, children: [_jsxs("p", { style: { fontWeight: 600, marginBottom: 4 }, children: ["\u26A0 ", risk.hypothesis] }), _jsxs("p", { className: "text-muted", style: { fontSize: 12 }, children: ["Component: ", _jsx("span", { className: "mono", children: risk.component_id })] }), _jsx("p", { className: "text-muted", style: { fontSize: 12 }, children: risk.reason_unresolved })] }, i))) })] })), report.documentation_gaps.length > 0 && (_jsxs("section", { style: { marginBottom: 24 }, children: [_jsxs("h3", { style: { marginBottom: 10 }, children: ["Documentation Gaps (", report.documentation_gaps.length, ")"] }), _jsx("div", { style: { display: "flex", flexDirection: "column", gap: 8 }, children: report.documentation_gaps.map((gap, i) => (_jsxs("div", { style: {
                                border: "1px solid var(--border)",
                                borderRadius: "var(--radius)",
                                overflow: "hidden",
                            }, children: [_jsxs("div", { style: {
                                        padding: "8px 12px",
                                        background: "var(--surface)",
                                        display: "flex",
                                        justifyContent: "space-between",
                                    }, children: [_jsx("span", { className: "mono", style: { fontSize: 12 }, children: gap.file }), _jsx("span", { className: "text-muted", style: { fontSize: 12 }, children: gap.reason })] }), _jsxs("div", { style: { display: "flex" }, children: [_jsx("pre", { className: "mono", style: {
                                                flex: 1,
                                                padding: "8px 10px",
                                                background: "#fff1f2",
                                                fontSize: 11,
                                                whiteSpace: "pre-wrap",
                                                wordBreak: "break-all",
                                                borderRight: "1px solid var(--border)",
                                            }, children: gap.current_text }), _jsx("pre", { className: "mono", style: {
                                                flex: 1,
                                                padding: "8px 10px",
                                                background: "#f0fdf4",
                                                fontSize: 11,
                                                whiteSpace: "pre-wrap",
                                                wordBreak: "break-all",
                                            }, children: gap.proposed_text })] })] }, i))) })] })), showPrSummary && (_jsx("div", { style: {
                    position: "fixed",
                    inset: 0,
                    background: "rgba(0,0,0,0.4)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    zIndex: 1000,
                }, onClick: () => setShowPrSummary(false), children: _jsxs("div", { style: {
                        background: "var(--bg)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius)",
                        padding: 24,
                        maxWidth: 680,
                        width: "100%",
                        maxHeight: "80vh",
                        overflowY: "auto",
                        boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
                    }, onClick: (e) => e.stopPropagation(), children: [_jsxs("div", { style: {
                                display: "flex",
                                justifyContent: "space-between",
                                marginBottom: 16,
                            }, children: [_jsx("h2", { children: "PR Summary" }), _jsx("button", { className: "btn btn-secondary", style: { padding: "3px 10px" }, onClick: () => setShowPrSummary(false), children: "\u2715" })] }), _jsx("pre", { style: {
                                whiteSpace: "pre-wrap",
                                wordBreak: "break-word",
                                fontSize: 13,
                                lineHeight: 1.7,
                                fontFamily: "inherit",
                            }, children: report.pr_summary }), _jsxs("p", { className: "text-muted", style: { fontSize: 11, marginTop: 12 }, children: ["Generated at ", new Date(report.generated_at).toLocaleString()] })] }) }))] }));
}
