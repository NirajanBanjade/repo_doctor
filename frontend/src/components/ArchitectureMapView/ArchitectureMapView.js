import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMemo, useState } from "react";
import ReactFlow, { Background, Controls, MiniMap, } from "reactflow";
import "reactflow/dist/style.css";
import { useTriggerXRay, useXRayGraph } from "@/hooks/useSession";
import Spinner from "@/components/Spinner";
function featureFlow(features) {
    const nodes = features.map((feature, index) => ({
        id: feature.feature_id,
        position: { x: (index % 3) * 300, y: Math.floor(index / 3) * 170 },
        data: {
            label: (_jsxs("div", { title: feature.files.join("\n"), style: {
                    width: "100%",
                    minWidth: 0,
                    whiteSpace: "normal",
                    overflowWrap: "anywhere",
                    wordBreak: "break-word",
                }, children: [_jsx("strong", { style: { display: "block", overflowWrap: "anywhere" }, children: feature.name }), _jsx("p", { style: {
                            fontSize: 11,
                            lineHeight: 1.45,
                            margin: "5px 0 0",
                            overflowWrap: "anywhere",
                        }, children: feature.description }), _jsxs("span", { style: { fontSize: 10, color: "var(--muted)" }, children: [feature.files.length, " files \u00B7 hover to inspect"] })] })),
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
    const edges = features.flatMap((feature) => feature.connected_feature_ids
        .filter((target) => ids.has(target))
        .map((target) => ({
        id: `${feature.feature_id}:${target}`,
        source: feature.feature_id,
        target,
        animated: true,
    })));
    return { nodes, edges };
}
function fileFlow(feature) {
    const nodes = feature.files.map((path, index) => ({
        id: path,
        position: { x: (index % 3) * 280, y: Math.floor(index / 3) * 130 },
        data: {
            label: (_jsxs("div", { style: {
                    width: "100%",
                    minWidth: 0,
                    whiteSpace: "normal",
                    overflowWrap: "anywhere",
                }, children: [_jsx("strong", { children: path.split("/").at(-1) }), _jsx("div", { style: { fontSize: 10, overflowWrap: "anywhere" }, children: path })] })),
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
export default function ArchitectureMapView({ sessionId }) {
    const { data, isPending, error } = useXRayGraph(sessionId);
    const { mutate: trigger, isPending: isTriggering } = useTriggerXRay(sessionId);
    const [selected, setSelected] = useState(null);
    const flow = useMemo(() => (selected ? fileFlow(selected) : featureFlow(data?.features ?? [])), [data, selected]);
    if (isPending)
        return (_jsxs("div", { style: { padding: 32 }, children: [_jsx(Spinner, {}), " Loading architecture\u2026"] }));
    if (error)
        return (_jsx("div", { style: { padding: 32 }, className: "text-danger", children: error.message }));
    if (!data || data.features.length === 0)
        return (_jsxs("div", { style: { padding: 32 }, children: [_jsx("p", { style: { marginBottom: 12 }, children: "Run X-Ray to build the feature map from the supplied wiki." }), _jsx("button", { className: "btn btn-primary", disabled: isTriggering, onClick: () => trigger(), children: isTriggering ? "Building…" : "Build Feature X-Ray" })] }));
    return (_jsxs("div", { style: { height: "100%", minHeight: 620, position: "relative" }, children: [_jsxs("div", { style: {
                    padding: "10px 16px",
                    borderBottom: "1px solid var(--border)",
                    display: "flex",
                    gap: 10,
                    alignItems: "center",
                }, children: [selected && (_jsx("button", { className: "btn btn-secondary", onClick: () => setSelected(null), children: "\u2190 All features" })), _jsx("strong", { children: selected ? selected.name : "Feature architecture" }), _jsx("span", { className: "text-muted", style: { fontSize: 12 }, children: selected
                            ? "File-level documented flow"
                            : "Click a feature to inspect its files" })] }), data.warnings.length > 0 && (_jsx("div", { style: { padding: 8, background: "#fef9c3", fontSize: 11 }, children: data.warnings.join(" · ") })), _jsx("div", { style: { height: "calc(100% - 48px)" }, children: _jsxs(ReactFlow, { nodes: flow.nodes, edges: flow.edges, onNodeClick: (_, node) => {
                        if (!selected)
                            setSelected(data.features.find((feature) => feature.feature_id === node.id) ?? null);
                    }, fitView: true, children: [_jsx(Background, {}), _jsx(Controls, {}), _jsx(MiniMap, {})] }) })] }));
}
