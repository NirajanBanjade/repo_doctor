import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useSession } from "@/hooks/useSession";
import { useSessionContext } from "@/context/SessionContext";
import StatusBadge from "@/components/StatusBadge";
import Spinner from "@/components/Spinner";
import ImportView from "@/components/ImportView";
import ArchitectureMapView from "@/components/ArchitectureMapView";
import EnvironmentDoctorView from "@/components/EnvironmentDoctorView";
import ImpactGraphView from "@/components/ImpactGraphView";
import TestPlanView from "@/components/TestPlanView";
import TestResultsView from "@/components/TestResultsView";
import VerificationView from "@/components/VerificationView";
const TAB_LABELS = {
    xray: "Architecture X-Ray",
    environment: "Environment Doctor",
    firstpr: "First PR",
    impact: "Impact Scope",
    tests: "Test Plan",
    results: "Test Results",
    verify: "Verification",
};
function Workspace({ sessionId }) {
    const [activeTab, setActiveTab] = useState("xray");
    const { data: session, isPending } = useSession(sessionId);
    const { clearSession } = useSessionContext();
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", height: "100vh" }, children: [_jsxs("header", { style: {
                    height: 52,
                    display: "flex",
                    alignItems: "center",
                    padding: "0 20px",
                    borderBottom: "1px solid var(--border)",
                    background: "var(--bg)",
                    gap: 16,
                    flexShrink: 0,
                }, children: [_jsxs("span", { style: { fontWeight: 700, fontSize: 16 }, children: [_jsx("span", { style: { color: "var(--accent)" }, children: "Repo" }), "Doc"] }), _jsx("span", { className: "text-muted", style: { fontSize: 12 }, children: session?.repo_path ?? "" }), _jsxs("span", { style: { marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }, children: [isPending ? (_jsx(Spinner, { size: 14 })) : session ? (_jsx(StatusBadge, { status: session.status })) : null, _jsx("button", { className: "btn btn-secondary", style: { padding: "4px 12px", fontSize: 12 }, onClick: clearSession, children: "\u2190 Back" })] })] }), _jsx("nav", { style: {
                    display: "flex",
                    borderBottom: "1px solid var(--border)",
                    background: "var(--surface)",
                    flexShrink: 0,
                    overflowX: "auto",
                }, children: Object.keys(TAB_LABELS)
                    .filter((tab) => tab !== "firstpr")
                    .map((tab) => {
                    return (_jsx("button", { onClick: () => setActiveTab(tab), style: {
                            padding: "10px 18px",
                            border: "none",
                            borderBottom: activeTab === tab
                                ? "2px solid var(--accent)"
                                : "2px solid transparent",
                            background: "none",
                            color: activeTab === tab ? "var(--accent)" : "var(--text)",
                            fontWeight: activeTab === tab ? 600 : 400,
                            fontSize: 13,
                            whiteSpace: "nowrap",
                            cursor: "pointer",
                        }, children: TAB_LABELS[tab] }, tab));
                }) }), _jsxs("main", { style: { flex: 1, overflowY: "auto", minHeight: 0 }, children: [activeTab === "xray" && _jsx(ArchitectureMapView, { sessionId: sessionId }), activeTab === "environment" && _jsx(EnvironmentDoctorView, { sessionId: sessionId }), activeTab === "impact" && (_jsx(ImpactGraphView, { sessionId: sessionId, onPlanCreated: () => setActiveTab("tests") })), activeTab === "tests" && (_jsx(TestPlanView, { sessionId: sessionId, onRan: () => setActiveTab("results") })), activeTab === "results" && _jsx(TestResultsView, { sessionId: sessionId }), activeTab === "verify" && _jsx(VerificationView, { sessionId: sessionId })] })] }));
}
export default function App() {
    const { session } = useSessionContext();
    if (!session) {
        return (_jsx(ImportView, { onSessionCreated: () => {
                // Session is set in context by useCreateSession; re-render is automatic
            } }));
    }
    return _jsx(Workspace, { sessionId: session.session_id });
}
