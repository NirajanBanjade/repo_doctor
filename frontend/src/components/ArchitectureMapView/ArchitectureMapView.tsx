import { useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { useTriggerXRay, useXRayGraph } from "@/hooks/useSession";
import Spinner from "@/components/Spinner";
import type { FeatureArchitecture } from "@/types";

interface Props {
  sessionId: string;
}

function featureFlow(features: FeatureArchitecture[]): {
  nodes: Node[];
  edges: Edge[];
} {
  const nodes: Node[] = features.map((feature, index) => ({
    id: feature.feature_id,
    position: { x: (index % 3) * 300, y: Math.floor(index / 3) * 170 },
    data: {
      label: (
        <div
          title={feature.files.join("\n")}
          style={{
            width: "100%",
            minWidth: 0,
            whiteSpace: "normal",
            overflowWrap: "anywhere",
            wordBreak: "break-word",
          }}
        >
          <strong style={{ display: "block", overflowWrap: "anywhere" }}>
            {feature.name}
          </strong>
          <p
            style={{
              fontSize: 11,
              lineHeight: 1.45,
              margin: "5px 0 0",
              overflowWrap: "anywhere",
            }}
          >
            {feature.description}
          </p>
          <span style={{ fontSize: 10, color: "var(--muted)" }}>
            {feature.files.length} files · hover to inspect
          </span>
        </div>
      ),
    },
    style: {
      width: 270,
      boxSizing: "border-box",
      overflow: "hidden",
      border: "2px solid var(--accent)",
      borderRadius: 8,
      background: "#fff",
    },
  }));
  const ids = new Set(features.map((feature) => feature.feature_id));
  const edges = features.flatMap((feature) =>
    feature.connected_feature_ids
      .filter((target) => ids.has(target))
      .map((target) => ({
        id: `${feature.feature_id}:${target}`,
        source: feature.feature_id,
        target,
        animated: true,
      })),
  );
  return { nodes, edges };
}

function fileFlow(feature: FeatureArchitecture): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = feature.files.map((path, index) => ({
    id: path,
    position: { x: (index % 3) * 280, y: Math.floor(index / 3) * 130 },
    data: {
      label: (
        <div
          style={{
            width: "100%",
            minWidth: 0,
            whiteSpace: "normal",
            overflowWrap: "anywhere",
          }}
        >
          <strong>{path.split("/").at(-1)}</strong>
          <div style={{ fontSize: 10, overflowWrap: "anywhere" }}>{path}</div>
        </div>
      ),
    },
    style: {
      border: `2px solid ${feature.frontend_files.includes(path) ? "#7c5cd8" : "#16a34a"}`,
      width: 250,
      boxSizing: "border-box",
      overflow: "hidden",
      borderRadius: 7,
      background: "#fff",
    },
  }));
  const edges = feature.file_edges.map((edge, index) => ({
    id: `${edge.source}:${edge.target}:${index}`,
    source: edge.source,
    target: edge.target,
    label: "documented flow",
  }));
  return { nodes, edges };
}

export default function ArchitectureMapView({ sessionId }: Props) {
  const { data, isPending, error } = useXRayGraph(sessionId);
  const { mutate: trigger, isPending: isTriggering } = useTriggerXRay(sessionId);
  const [selected, setSelected] = useState<FeatureArchitecture | null>(null);
  const flow = useMemo(
    () => (selected ? fileFlow(selected) : featureFlow(data?.features ?? [])),
    [data, selected],
  );

  if (isPending)
    return (
      <div style={{ padding: 32 }}>
        <Spinner /> Loading architecture…
      </div>
    );
  if (error)
    return (
      <div style={{ padding: 32 }} className="text-danger">
        {error.message}
      </div>
    );
  if (!data || data.features.length === 0)
    return (
      <div style={{ padding: 32 }}>
        <p style={{ marginBottom: 12 }}>
          Run X-Ray to build the feature map from the supplied wiki.
        </p>
        <button
          className="btn btn-primary"
          disabled={isTriggering}
          onClick={() => trigger()}
        >
          {isTriggering ? "Building…" : "Build Feature X-Ray"}
        </button>
      </div>
    );

  return (
    <div style={{ height: "100%", minHeight: 620, position: "relative" }}>
      <div
        style={{
          padding: "10px 16px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          gap: 10,
          alignItems: "center",
        }}
      >
        {selected && (
          <button className="btn btn-secondary" onClick={() => setSelected(null)}>
            ← All features
          </button>
        )}
        <strong>{selected ? selected.name : "Feature architecture"}</strong>
        <span className="text-muted" style={{ fontSize: 12 }}>
          {selected
            ? "File-level documented flow"
            : "Click a feature to inspect its files"}
        </span>
      </div>
      {data.warnings.length > 0 && (
        <div style={{ padding: 8, background: "#fef9c3", fontSize: 11 }}>
          {data.warnings.join(" · ")}
        </div>
      )}
      <div style={{ height: "calc(100% - 48px)" }}>
        <ReactFlow
          nodes={flow.nodes}
          edges={flow.edges}
          onNodeClick={(_, node) => {
            if (!selected)
              setSelected(
                data.features.find((feature) => feature.feature_id === node.id) ?? null,
              );
          }}
          fitView
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    </div>
  );
}
