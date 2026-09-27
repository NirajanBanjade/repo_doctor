import { useState, useMemo, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from "reactflow";
import "reactflow/dist/style.css";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createTestPlan, triggerImpact, getImpactGraph } from "@/api/client";
import EvidencePanel from "@/components/EvidencePanel";
import Spinner from "@/components/Spinner";
import { useXRayGraph } from "@/hooks/useSession";
import type { ImpactNode, ImpactRunResult, EvidenceRef } from "@/types";

const DEPTH_COLOR = ["#3b82d4", "#7c5cd8", "#16a34a", "#d97706"];

function buildFlow(result: ImpactRunResult): { rfNodes: Node[]; rfEdges: Edge[] } {
  const COL = Math.ceil(Math.sqrt(result.nodes.length)) || 1;
  const rfNodes: Node[] = result.nodes.map((in_: ImpactNode, i) => {
    const color = DEPTH_COLOR[Math.min(in_.depth_level, DEPTH_COLOR.length - 1)];
    const isOrigin = in_.depth_level === 0;
    return {
      id: in_.node_id,
      position: { x: (i % COL) * 240, y: Math.floor(i / COL) * 130 },
      data: {
        label: (
          <div
            style={{
              width: "100%",
              minWidth: 0,
              fontSize: 11,
              lineHeight: 1.4,
              whiteSpace: "normal",
              overflowWrap: "anywhere",
            }}
          >
            <div style={{ fontWeight: 600, color }}>{in_.node.name}</div>
            <div style={{ color: "#57606a" }}>{in_.node.path}</div>
            <div style={{ color: "#57606a", fontSize: 10 }}>
              {result.primary_feature && isOrigin
                ? "primary feature scope"
                : `impact depth ${in_.depth_level}`}
            </div>
          </div>
        ),
      },
      style: {
        background: isOrigin ? color + "22" : "#fff",
        border: `2px solid ${color}`,
        borderRadius: 6,
        padding: "8px 10px",
        width: 220,
        boxSizing: "border-box",
        overflow: "hidden",
      },
    };
  });

  const rfEdges: Edge[] = result.edges.map((e) => ({
    id: e.edge_id,
    source: e.source_id,
    target: e.target_id,
    label: e.relationship,
    animated: e.evidence_status === "inferred",
    style: {
      stroke:
        e.evidence_status === "inferred"
          ? "#d97706"
          : e.evidence_status === "observed_test"
            ? "#3b82d4"
            : "#16a34a",
    },
    labelStyle: { fontSize: 10, fill: "#57606a" },
  }));

  return { rfNodes, rfEdges };
}

interface Props {
  sessionId: string;
  onPlanCreated?: () => void;
}

export default function ImpactGraphView({ sessionId, onPlanCreated }: Props) {
  const qc = useQueryClient();
  const [symbolId, setSymbolId] = useState("");
  const [gitDiff, setGitDiff] = useState("");
  const [depth, setDepth] = useState<1 | 2 | 3>(2);
  const [featureId, setFeatureId] = useState("");
  const [mode, setMode] = useState<"feature" | "symbol" | "diff">("feature");
  const [selectedNode, setSelectedNode] = useState<ImpactNode | null>(null);
  const [selectedNodeIds, setSelectedNodeIds] = useState<Set<string>>(new Set());
  const { data: xray } = useXRayGraph(sessionId);

  const { data: impactResult, isPending: isFetching } = useQuery({
    queryKey: ["impact", sessionId],
    queryFn: () => getImpactGraph(sessionId),
    enabled: false, // only fetch after trigger
    retry: false,
  });

  const { mutate: trigger, isPending: isTriggering } = useMutation({
    mutationFn: () =>
      triggerImpact(sessionId, {
        ...(mode === "feature"
          ? { feature_id: featureId }
          : mode === "symbol"
            ? { symbol_id: symbolId }
            : { git_diff: gitDiff }),
        depth,
      }),
    onSuccess: (result) => {
      qc.setQueryData(["impact", sessionId], result);
      setSelectedNodeIds(new Set(result.nodes.map((node) => node.node_id)));
      void qc.invalidateQueries({ queryKey: ["session", sessionId] });
    },
  });
  const { mutate: makePlan, isPending: isPlanning } = useMutation({
    mutationFn: () =>
      createTestPlan(sessionId, {
        impact_run_id: impactResult!.run_id,
        selected_node_ids: [...selectedNodeIds],
      }),
    onSuccess: (plan) => {
      qc.setQueryData(["testplan", sessionId], plan);
      onPlanCreated?.();
    },
  });

  const { rfNodes, rfEdges } = useMemo(() => {
    if (!impactResult) return { rfNodes: [], rfEdges: [] };
    return buildFlow(impactResult);
  }, [impactResult]);

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_evt, rfNode) => {
      const n = impactResult?.nodes.find((x) => x.node_id === rfNode.id) ?? null;
      setSelectedNode(n);
    },
    [impactResult],
  );

  const selectedEvidence: EvidenceRef[] = selectedNode
    ? impactResult!.edges
        .filter(
          (e) =>
            e.source_id === selectedNode.node_id ||
            e.target_id === selectedNode.node_id,
        )
        .map((e) => ({
          file: e.file,
          line: e.line,
          snippet: e.note,
          evidence_status: e.evidence_status,
        }))
    : [];

  return (
    <div style={{ padding: 0, height: "100%" }}>
      {/* Control bar */}
      <div
        style={{
          padding: "14px 20px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          gap: 12,
          alignItems: "flex-end",
          flexWrap: "wrap",
          background: "var(--surface)",
        }}
      >
        <div>
          <label
            style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}
          >
            Mode
          </label>
          <div style={{ display: "flex", gap: 6 }}>
            {(["feature", "symbol", "diff"] as const).map((m) => (
              <button
                key={m}
                className={`btn ${mode === m ? "btn-primary" : "btn-secondary"}`}
                style={{ padding: "5px 12px", fontSize: 12 }}
                onClick={() => setMode(m)}
              >
                {m === "feature" ? "Feature" : m === "symbol" ? "File ID" : "Git Diff"}
              </button>
            ))}
          </div>
        </div>

        {mode === "feature" ? (
          <div style={{ flex: 1, minWidth: 220 }}>
            <label
              style={{
                fontSize: 12,
                fontWeight: 600,
                display: "block",
                marginBottom: 4,
              }}
            >
              Primary feature
            </label>
            <select
              value={featureId}
              onChange={(e) => setFeatureId(e.target.value)}
              style={{ marginBottom: 0 }}
            >
              <option value="">Select a feature…</option>
              {(xray?.features ?? []).map((feature) => (
                <option key={feature.feature_id} value={feature.feature_id}>
                  {feature.name}
                </option>
              ))}
            </select>
          </div>
        ) : mode === "symbol" ? (
          <div style={{ flex: 1, minWidth: 200 }}>
            <label
              style={{
                fontSize: 12,
                fontWeight: 600,
                display: "block",
                marginBottom: 4,
              }}
            >
              Symbol ID
            </label>
            <input
              type="text"
              value={symbolId}
              onChange={(e) => setSymbolId(e.target.value)}
              placeholder="e.g. app/main.py::create_app"
              style={{ marginBottom: 0 }}
            />
          </div>
        ) : (
          <div style={{ flex: 1, minWidth: 200 }}>
            <label
              style={{
                fontSize: 12,
                fontWeight: 600,
                display: "block",
                marginBottom: 4,
              }}
            >
              Git Diff
            </label>
            <textarea
              value={gitDiff}
              onChange={(e) => setGitDiff(e.target.value)}
              placeholder="Paste unified diff here…"
              rows={3}
              style={{ marginBottom: 0, resize: "vertical" }}
            />
          </div>
        )}

        <div>
          <label
            style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}
          >
            Depth
          </label>
          <div style={{ display: "flex", gap: 6 }}>
            {([1, 2, 3] as const).map((d) => (
              <button
                key={d}
                className={`btn ${depth === d ? "btn-primary" : "btn-secondary"}`}
                style={{ padding: "5px 10px", fontSize: 12 }}
                onClick={() => setDepth(d)}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        <button
          className="btn btn-primary"
          onClick={() => trigger()}
          disabled={
            isTriggering ||
            (mode === "feature"
              ? !featureId
              : mode === "symbol"
                ? !symbolId.trim()
                : !gitDiff.trim())
          }
        >
          {isTriggering ? (
            <>
              <Spinner size={13} /> Analysing…
            </>
          ) : (
            "Analyse Impact"
          )}
        </button>
      </div>

      {/* Graph area */}
      {isFetching && (
        <div style={{ display: "flex", gap: 10, alignItems: "center", padding: 32 }}>
          <Spinner /> Building impact graph…
        </div>
      )}

      {impactResult && !isFetching && (
        <div style={{ display: "flex", height: "calc(100% - 80px)", minHeight: 520 }}>
          <div style={{ flex: 1 }}>
            <div
              style={{
                padding: "10px 12px",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                  marginBottom: 8,
                }}
              >
                <div>
                  <strong style={{ fontSize: 13 }}>Test plan scope</strong>
                  <span className="text-muted" style={{ marginLeft: 8, fontSize: 12 }}>
                    {selectedNodeIds.size} of {impactResult.nodes.length} impacted files
                  </span>
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: "3px 8px", fontSize: 11 }}
                    onClick={() =>
                      setSelectedNodeIds(
                        new Set(impactResult.nodes.map((node) => node.node_id)),
                      )
                    }
                  >
                    Select all
                  </button>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: "3px 8px", fontSize: 11 }}
                    onClick={() => setSelectedNodeIds(new Set())}
                  >
                    Clear
                  </button>
                </div>
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 6,
                  marginBottom: 10,
                }}
              >
                {impactResult.nodes.map((impactNode) => {
                  const included = selectedNodeIds.has(impactNode.node_id);
                  return (
                    <button
                      key={impactNode.node_id}
                      className={`btn ${included ? "btn-primary" : "btn-secondary"}`}
                      style={{ padding: "3px 8px", fontSize: 11 }}
                      title={impactNode.node.path}
                      onClick={() =>
                        setSelectedNodeIds((current) => {
                          const next = new Set(current);
                          if (included) next.delete(impactNode.node_id);
                          else next.add(impactNode.node_id);
                          return next;
                        })
                      }
                    >
                      {impactNode.node.name}
                    </button>
                  );
                })}
              </div>
              <button
                className="btn btn-primary"
                disabled={isPlanning || selectedNodeIds.size === 0}
                onClick={() => makePlan()}
              >
                {isPlanning
                  ? "Creating test plan…"
                  : `Create Test Plan for ${selectedNodeIds.size} File${selectedNodeIds.size === 1 ? "" : "s"}`}
              </button>
            </div>
            {impactResult.warnings.length > 0 && (
              <div
                style={{
                  margin: 8,
                  padding: "6px 12px",
                  background: "#fef9c3",
                  border: "1px solid #d97706",
                  borderRadius: "var(--radius)",
                  fontSize: 12,
                  color: "#92400e",
                }}
              >
                {impactResult.warnings.join(" · ")}
              </div>
            )}
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              onNodeClick={handleNodeClick}
              fitView
              fitViewOptions={{ padding: 0.15 }}
            >
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
            {(impactResult.external_feature_suggestions?.length ?? 0) > 0 && (
              <div
                style={{
                  margin: 8,
                  padding: 10,
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  fontSize: 12,
                }}
              >
                <strong>Suggested cross-feature regression scopes:</strong>{" "}
                {impactResult
                  .external_feature_suggestions!.map((feature) => feature.name)
                  .join(", ")}
              </div>
            )}
          </div>

          {selectedNode && (
            <div
              style={{
                width: 300,
                borderLeft: "1px solid var(--border)",
                padding: 12,
                overflowY: "auto",
              }}
            >
              <h3 style={{ marginBottom: 4 }}>{selectedNode.node.name}</h3>
              <p className="mono text-muted" style={{ marginBottom: 8 }}>
                {selectedNode.node.path}
              </p>
              <p style={{ fontSize: 12, marginBottom: 8 }}>
                <strong>Depth:</strong> {selectedNode.depth_level}
              </p>
              {selectedNode.existing_tests.length > 0 && (
                <div style={{ marginBottom: 10 }}>
                  <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                    Existing tests
                  </p>
                  {selectedNode.existing_tests.map((t) => (
                    <p
                      key={t}
                      className="mono"
                      style={{ fontSize: 11, color: "var(--accent)" }}
                    >
                      {t}
                    </p>
                  ))}
                </div>
              )}
              {/* Annotations */}
              {impactResult.annotations
                .filter((a) => a.node_id === selectedNode.node_id)
                .map((a) => (
                  <div
                    key={a.node_id}
                    style={{
                      padding: "8px 10px",
                      background: "#fef9c3",
                      border: "1px solid #d97706",
                      borderRadius: "var(--radius)",
                      fontSize: 12,
                      marginBottom: 8,
                    }}
                  >
                    <strong>⚠ {a.hypothesis_label}:</strong> {a.risk}
                  </div>
                ))}
              <EvidencePanel
                refs={selectedEvidence}
                onClose={() => setSelectedNode(null)}
              />
            </div>
          )}
        </div>
      )}

      {!impactResult && !isFetching && (
        <div style={{ padding: 32, color: "var(--muted)" }}>
          Enter a symbol ID or diff above and click <strong>Analyse Impact</strong>.
        </div>
      )}
    </div>
  );
}
