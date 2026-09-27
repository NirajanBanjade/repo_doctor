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

type Tab =
  "xray" | "environment" | "firstpr" | "impact" | "tests" | "results" | "verify";

const TAB_LABELS: Record<Tab, string> = {
  xray: "Architecture X-Ray",
  environment: "Environment Doctor",
  firstpr: "First PR",
  impact: "Impact Scope",
  tests: "Test Plan",
  results: "Test Results",
  verify: "Verification",
};

interface WorkspaceProps {
  sessionId: string;
}

function Workspace({ sessionId }: WorkspaceProps) {
  const [activeTab, setActiveTab] = useState<Tab>("xray");
  const { data: session, isPending } = useSession(sessionId);
  const { clearSession } = useSessionContext();

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* Top bar */}
      <header
        style={{
          height: 52,
          display: "flex",
          alignItems: "center",
          padding: "0 20px",
          borderBottom: "1px solid var(--border)",
          background: "var(--bg)",
          gap: 16,
          flexShrink: 0,
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 16 }}>
          <span style={{ color: "var(--accent)" }}>Repo</span>Doc
        </span>
        <span className="text-muted" style={{ fontSize: 12 }}>
          {session?.repo_path ?? ""}
        </span>
        <span
          style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}
        >
          {isPending ? (
            <Spinner size={14} />
          ) : session ? (
            <StatusBadge status={session.status} />
          ) : null}
          <button
            className="btn btn-secondary"
            style={{ padding: "4px 12px", fontSize: 12 }}
            onClick={clearSession}
          >
            ← Back
          </button>
        </span>
      </header>

      {/* Tab bar */}
      <nav
        style={{
          display: "flex",
          borderBottom: "1px solid var(--border)",
          background: "var(--surface)",
          flexShrink: 0,
          overflowX: "auto",
        }}
      >
        {(Object.keys(TAB_LABELS) as Tab[])
          .filter((tab) => tab !== "firstpr")
          .map((tab) => {
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  padding: "10px 18px",
                  border: "none",
                  borderBottom:
                    activeTab === tab
                      ? "2px solid var(--accent)"
                      : "2px solid transparent",
                  background: "none",
                  color: activeTab === tab ? "var(--accent)" : "var(--text)",
                  fontWeight: activeTab === tab ? 600 : 400,
                  fontSize: 13,
                  whiteSpace: "nowrap",
                  cursor: "pointer",
                }}
              >
                {TAB_LABELS[tab]}
              </button>
            );
          })}
      </nav>

      {/* Content */}
      <main style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
        {activeTab === "xray" && <ArchitectureMapView sessionId={sessionId} />}
        {activeTab === "environment" && <EnvironmentDoctorView sessionId={sessionId} />}
        {activeTab === "impact" && (
          <ImpactGraphView
            sessionId={sessionId}
            onPlanCreated={() => setActiveTab("tests")}
          />
        )}
        {activeTab === "tests" && (
          <TestPlanView
            sessionId={sessionId}
            onRan={() => setActiveTab("results")}
          />
        )}
        {activeTab === "results" && <TestResultsView sessionId={sessionId} />}
        {activeTab === "verify" && <VerificationView sessionId={sessionId} />}
      </main>
    </div>
  );
}

export default function App() {
  const { session } = useSessionContext();

  if (!session) {
    return (
      <ImportView
        onSessionCreated={() => {
          // Session is set in context by useCreateSession; re-render is automatic
        }}
      />
    );
  }

  return <Workspace sessionId={session.session_id} />;
}
