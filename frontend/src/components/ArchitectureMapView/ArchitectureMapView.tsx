import { useState, useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from "reactflow";
import "reactflow/dist/style.css";
import { useXRayGraph, useTriggerXRay } from "@/hooks/useSession";
import EvidencePanel from "@/components/EvidencePanel";
import Spinner from "@/components/Spinner";
import type { GraphNode, GraphEdge, EvidenceRef } from "@/types";

// ── colour map ────────────────────────────────────────
const KIND_COLOR: Record<GraphNode["kind"], string> = {
  module: "#3b82d4",
  class: "#7c5cd8",
  function: "#16a34a",
  file: "#57606a",
};

const EVIDENCE_DASH: Record<GraphEdge["evidence_status"], string> = {
  confirmed_static: "0",
  observed_test: "0",
  inferred: "6 3",
};

const EDGE_COLOR: Record<GraphEdge["evidence_status"], string> = {
  confirmed_static: "#16a34a",
  observed_test: "#3b82d4",
  inferred: "#d97706",
};

function buildFlow(
  nodes: GraphNode[],
  edges: GraphEdge[],
): { rfNodes: Node[]; rfEdges: Edge[] } {
  const COL_SIZE = Math.ceil(Math.sqrt(nodes.length)) || 1;
  const rfNodes: Node[] = nodes.map((n, i) => ({
    id: n.node_id,
    position: { x: (i % COL_SIZE) * 220, y: Math.floor(i / COL_SIZE) * 120 },
    data: {
      label: (
        <div style={{ fontSize: 11, lineHeight: 1.4 }}>
          <div
            style={{
              fontWeight: 600,
              color: KIND_COLOR[n.kind],
              marginBottom: 2,
            }}
          >
            {n.name}
          </div>
          <div style={{ color: "#57606a" }}>
            {n.path}:{n.line_start}
          </div>
          {n.key_module && (
            <div style={{ color: "#d97706", fontSize: 10 }}>★ key module</div>
          )}
        </div>
      ),
    },
    style: {
      background: "#fff",
      border: `2px solid ${KIND_COLOR[n.kind]}`,
      borderRadius: 6,
      padding: "8px 10px",
      fontSize: 12,
      boxShadow: n.key_module ? `0 0 0 3px ${KIND_COLOR[n.kind]}44` : undefined,
    },
  }));

  const rfEdges: Edge[] = edges.map((e) => ({
    id: e.edge_id,
    source: e.source_id,
    target: e.target_id,
    label: e.relationship,
    animated: e.evidence_status === "inferred",
    style: {
      stroke: EDGE_COLOR[e.evidence_status],
      strokeDasharray: EVIDENCE_DASH[e.evidence_status],
    },
    labelStyle: { fontSize: 10, fill: "#57606a" },
    labelBgStyle: { fill: "#fff", fillOpacity: 0.8 },
  }));

  return { rfNodes, rfEdges };
}

interface Props {
  sessionId: string;
}

export default function ArchitectureMapView({ sessionId }: Props) {
  const { data: xray, isPending, error } = useXRayGraph(sessionId);
  const { mutate: triggerXRay, isPending: isTriggering } =
    useTriggerXRay(sessionId);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const { rfNodes, rfEdges } = useMemo(() => {
    if (!xray) return { rfNodes: [], rfEdges: [] };
    return buildFlow(xray.nodes, xray.edges);
  }, [xray]);

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_evt, rfNode) => {
      const node = xray?.nodes.find((n) => n.node_id === rfNode.id) ?? null;
      setSelectedNode(node);
    },
    [xray],
  );

  if (isPending) {
    return (
      <div
        style={{
          display: "flex",
          gap: 10,
          alignItems: "center",
          padding: 32,
        }}
      >
        <Spinner /> Loading architecture graph…
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 32 }}>
        <p className="text-danger" style={{ marginBottom: 12 }}>
          Failed to load graph: {error.message}
        </p>
        <button
          className="btn btn-primary"
          onClick={() => triggerXRay()}
          disabled={isTriggering}
        >
          {isTriggering ? "Running X-Ray…" : "Run X-Ray"}
        </button>
      </div>
    );
  }

  if (!xray) {
    return (
      <div style={{ padding: 32 }}>
        <p className="text-muted" style={{ marginBottom: 12 }}>
          No X-Ray data yet. Trigger a scan to build the architecture map.
        </p>
        <button
          className="btn btn-primary"
          onClick={() => triggerXRay()}
          disabled={isTriggering}
        >
          {isTriggering ? "Running X-Ray…" : "Run Repository X-Ray"}
        </button>
      </div>
    );
  }

  if (xray.nodes.length === 0) {
    return (
      <div style={{ padding: 32 }}>
        <p className="text-muted" style={{ marginBottom: 12 }}>
          No architecture nodes have been extracted yet.
        </p>
        <button
          className="btn btn-primary"
          onClick={() => triggerXRay()}
          disabled={isTriggering}
        >
          {isTriggering ? "Running X-Ray…" : "Run Repository X-Ray"}
        </button>
      </div>
    );
  }

  const selectedEvidence: EvidenceRef[] = selectedNode
    ? xray.edges
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
    <div style={{ display: "flex", height: "100%", minHeight: 600 }}>
      {/* Graph canvas */}
      <div style={{ flex: 1, position: "relative" }}>
        {/* Warnings bar */}
        {xray.warnings.length > 0 && (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              zIndex: 10,
              background: "#fef9c3",
              border: "1px solid #d97706",
              borderRadius: "var(--radius)",
              margin: 8,
              padding: "6px 12px",
              fontSize: 12,
              color: "#92400e",
            }}
          >
            {xray.warnings.join(" · ")}
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
          <MiniMap
            nodeColor={(n) => {
              const gn = xray.nodes.find((x) => x.node_id === n.id);
              return gn ? KIND_COLOR[gn.kind] : "#ccc";
            }}
          />
        </ReactFlow>

        {/* Legend */}
        <div
          style={{
            position: "absolute",
            bottom: 12,
            left: 12,
            background: "rgba(255,255,255,0.92)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            padding: "8px 12px",
            fontSize: 11,
            display: "flex",
            gap: 12,
          }}
        >
          {Object.entries(KIND_COLOR).map(([kind, color]) => (
            <span key={kind} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  background: color,
                  borderRadius: 2,
                  display: "inline-block",
                }}
              />
              {kind}
            </span>
          ))}
        </div>
      </div>

      {/* Side panel */}
      {selectedNode && (
        <div style={{ width: 320, padding: 12, borderLeft: "1px solid var(--border)", overflowY: "auto" }}>
          <div style={{ marginBottom: 12 }}>
            <h3 style={{ marginBottom: 4 }}>{selectedNode.name}</h3>
            <p className="text-muted mono" style={{ marginBottom: 8 }}>
              {selectedNode.path}:{selectedNode.line_start}–{selectedNode.line_end}
            </p>
            <span
              style={{
                fontSize: 11,
                padding: "2px 8px",
                borderRadius: 10,
                background: KIND_COLOR[selectedNode.kind] + "22",
                color: KIND_COLOR[selectedNode.kind],
                border: `1px solid ${KIND_COLOR[selectedNode.kind]}44`,
              }}
            >
              {selectedNode.kind}
            </span>
          </div>

          {selectedNode.summary && (
            <p style={{ fontSize: 13, marginBottom: 12, color: "var(--text)" }}>
              {selectedNode.summary}
            </p>
          )}

          <EvidencePanel
            refs={selectedEvidence}
            onClose={() => setSelectedNode(null)}
          />
        </div>
      )}
    </div>
  );
}
