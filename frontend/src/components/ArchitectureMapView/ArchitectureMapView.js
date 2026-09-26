import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useCallback, useMemo } from "react";
import ReactFlow, { Background, Controls, MiniMap, } from "reactflow";
import "reactflow/dist/style.css";
import { useXRayGraph, useTriggerXRay } from "@/hooks/useSession";
import EvidencePanel from "@/components/EvidencePanel";
import Spinner from "@/components/Spinner";
// ── colour map ────────────────────────────────────────
const KIND_COLOR = {
    module: "#3b82d4",
    class: "#7c5cd8",
    function: "#16a34a",
    file: "#57606a",
};
const EVIDENCE_DASH = {
    confirmed_static: "0",
    observed_test: "0",
    inferred: "6 3",
};
const EDGE_COLOR = {
    confirmed_static: "#16a34a",
    observed_test: "#3b82d4",
    inferred: "#d97706",
};
function buildFlow(nodes, edges) {
    const COL_SIZE = Math.ceil(Math.sqrt(nodes.length)) || 1;
    const rfNodes = nodes.map((n, i) => ({
        id: n.node_id,
        position: { x: (i % COL_SIZE) * 220, y: Math.floor(i / COL_SIZE) * 120 },
        data: {
            label: (_jsxs("div", { style: { fontSize: 11, lineHeight: 1.4 }, children: [_jsx("div", { style: {
                            fontWeight: 600,
                            color: KIND_COLOR[n.kind],
                            marginBottom: 2,
                        }, children: n.name }), _jsxs("div", { style: { color: "#57606a" }, children: [n.path, ":", n.line_start] }), n.key_module && (_jsx("div", { style: { color: "#d97706", fontSize: 10 }, children: "\u2605 key module" }))] })),
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
    const rfEdges = edges.map((e) => ({
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
export default function ArchitectureMapView({ sessionId }) {
    const { data: xray, isPending, error } = useXRayGraph(sessionId);
    const { mutate: triggerXRay, isPending: isTriggering } = useTriggerXRay(sessionId);
    const [selectedNode, setSelectedNode] = useState(null);
    const { rfNodes, rfEdges } = useMemo(() => {
        if (!xray)
            return { rfNodes: [], rfEdges: [] };
        return buildFlow(xray.nodes, xray.edges);
    }, [xray]);
    const handleNodeClick = useCallback((_evt, rfNode) => {
        const node = xray?.nodes.find((n) => n.node_id === rfNode.id) ?? null;
        setSelectedNode(node);
    }, [xray]);
    if (isPending) {
        return (_jsxs("div", { style: {
                display: "flex",
                gap: 10,
                alignItems: "center",
                padding: 32,
            }, children: [_jsx(Spinner, {}), " Loading architecture graph\u2026"] }));
    }
    if (error) {
        return (_jsxs("div", { style: { padding: 32 }, children: [_jsxs("p", { className: "text-danger", style: { marginBottom: 12 }, children: ["Failed to load graph: ", error.message] }), _jsx("button", { className: "btn btn-primary", onClick: () => triggerXRay(), disabled: isTriggering, children: isTriggering ? "Running X-Ray…" : "Run X-Ray" })] }));
    }
    if (!xray) {
        return (_jsxs("div", { style: { padding: 32 }, children: [_jsx("p", { className: "text-muted", style: { marginBottom: 12 }, children: "No X-Ray data yet. Trigger a scan to build the architecture map." }), _jsx("button", { className: "btn btn-primary", onClick: () => triggerXRay(), disabled: isTriggering, children: isTriggering ? "Running X-Ray…" : "Run Repository X-Ray" })] }));
    }
    if (xray.nodes.length === 0) {
        return (_jsxs("div", { style: { padding: 32 }, children: [_jsx("p", { className: "text-muted", style: { marginBottom: 12 }, children: "No architecture nodes have been extracted yet." }), _jsx("button", { className: "btn btn-primary", onClick: () => triggerXRay(), disabled: isTriggering, children: isTriggering ? "Running X-Ray…" : "Run Repository X-Ray" })] }));
    }
    const selectedEvidence = selectedNode
        ? xray.edges
            .filter((e) => e.source_id === selectedNode.node_id ||
            e.target_id === selectedNode.node_id)
            .map((e) => ({
            file: e.file,
            line: e.line,
            snippet: e.note,
            evidence_status: e.evidence_status,
        }))
        : [];
    return (_jsxs("div", { style: { display: "flex", height: "100%", minHeight: 600 }, children: [_jsxs("div", { style: { flex: 1, position: "relative" }, children: [xray.warnings.length > 0 && (_jsx("div", { style: {
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
                        }, children: xray.warnings.join(" · ") })), _jsxs(ReactFlow, { nodes: rfNodes, edges: rfEdges, onNodeClick: handleNodeClick, fitView: true, fitViewOptions: { padding: 0.15 }, children: [_jsx(Background, {}), _jsx(Controls, {}), _jsx(MiniMap, { nodeColor: (n) => {
                                    const gn = xray.nodes.find((x) => x.node_id === n.id);
                                    return gn ? KIND_COLOR[gn.kind] : "#ccc";
                                } })] }), _jsx("div", { style: {
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
                        }, children: Object.entries(KIND_COLOR).map(([kind, color]) => (_jsxs("span", { style: { display: "flex", alignItems: "center", gap: 4 }, children: [_jsx("span", { style: {
                                        width: 10,
                                        height: 10,
                                        background: color,
                                        borderRadius: 2,
                                        display: "inline-block",
                                    } }), kind] }, kind))) })] }), selectedNode && (_jsxs("div", { style: { width: 320, padding: 12, borderLeft: "1px solid var(--border)", overflowY: "auto" }, children: [_jsxs("div", { style: { marginBottom: 12 }, children: [_jsx("h3", { style: { marginBottom: 4 }, children: selectedNode.name }), _jsxs("p", { className: "text-muted mono", style: { marginBottom: 8 }, children: [selectedNode.path, ":", selectedNode.line_start, "\u2013", selectedNode.line_end] }), _jsx("span", { style: {
                                    fontSize: 11,
                                    padding: "2px 8px",
                                    borderRadius: 10,
                                    background: KIND_COLOR[selectedNode.kind] + "22",
                                    color: KIND_COLOR[selectedNode.kind],
                                    border: `1px solid ${KIND_COLOR[selectedNode.kind]}44`,
                                }, children: selectedNode.kind })] }), selectedNode.summary && (_jsx("p", { style: { fontSize: 13, marginBottom: 12, color: "var(--text)" }, children: selectedNode.summary })), _jsx(EvidencePanel, { refs: selectedEvidence, onClose: () => setSelectedNode(null) })] }))] }));
}
