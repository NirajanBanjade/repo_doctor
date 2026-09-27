import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState, useMemo, useCallback } from "react";
import ReactFlow, { Background, Controls, MiniMap, } from "reactflow";
import "reactflow/dist/style.css";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createTestPlan, triggerImpact, getImpactGraph } from "@/api/client";
import EvidencePanel from "@/components/EvidencePanel";
import Spinner from "@/components/Spinner";
import { useXRayGraph } from "@/hooks/useSession";
const DEPTH_COLOR = ["#3b82d4", "#7c5cd8", "#16a34a", "#d97706"];
function buildFlow(result) {
    const COL = Math.ceil(Math.sqrt(result.nodes.length)) || 1;
    const rfNodes = result.nodes.map((in_, i) => {
        const color = DEPTH_COLOR[Math.min(in_.depth_level, DEPTH_COLOR.length - 1)];
        const isOrigin = in_.depth_level === 0;
        return {
            id: in_.node_id,
            position: { x: (i % COL) * 240, y: Math.floor(i / COL) * 130 },
            data: {
                label: (_jsxs("div", { style: {
                        width: "100%",
                        minWidth: 0,
                        fontSize: 11,
                        lineHeight: 1.4,
                        whiteSpace: "normal",
                        overflowWrap: "anywhere",
                    }, children: [_jsx("div", { style: { fontWeight: 600, color }, children: in_.node.name }), _jsx("div", { style: { color: "#57606a" }, children: in_.node.path }), _jsx("div", { style: { color: "#57606a", fontSize: 10 }, children: result.primary_feature && isOrigin
                                ? "primary feature scope"
                                : `impact depth ${in_.depth_level}` })] })),
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
    const rfEdges = result.edges.map((e) => ({
        id: e.edge_id,
        source: e.source_id,
        target: e.target_id,
        label: e.relationship,
        animated: e.evidence_status === "inferred",
        style: {
            stroke: e.evidence_status === "inferred"
                ? "#d97706"
                : e.evidence_status === "observed_test"
                    ? "#3b82d4"
                    : "#16a34a",
        },
        labelStyle: { fontSize: 10, fill: "#57606a" },
    }));
    return { rfNodes, rfEdges };
}
export default function ImpactGraphView({ sessionId, onPlanCreated }) {
    const qc = useQueryClient();
    const [symbolId, setSymbolId] = useState("");
    const [gitDiff, setGitDiff] = useState("");
    const [depth, setDepth] = useState(2);
    const [featureId, setFeatureId] = useState("");
    const [mode, setMode] = useState("feature");
    const [selectedNode, setSelectedNode] = useState(null);
    const [selectedNodeIds, setSelectedNodeIds] = useState(new Set());
    const { data: xray } = useXRayGraph(sessionId);
    const { data: impactResult, isPending: isFetching } = useQuery({
        queryKey: ["impact", sessionId],
        queryFn: () => getImpactGraph(sessionId),
        enabled: false, // only fetch after trigger
        retry: false,
    });
    const { mutate: trigger, isPending: isTriggering } = useMutation({
        mutationFn: () => triggerImpact(sessionId, {
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
        mutationFn: () => createTestPlan(sessionId, {
            impact_run_id: impactResult.run_id,
            selected_node_ids: [...selectedNodeIds],
        }),
        onSuccess: (plan) => {
            qc.setQueryData(["testplan", sessionId], plan);
            onPlanCreated?.();
        },
    });
    const { rfNodes, rfEdges } = useMemo(() => {
        if (!impactResult)
            return { rfNodes: [], rfEdges: [] };
        return buildFlow(impactResult);
    }, [impactResult]);
    const handleNodeClick = useCallback((_evt, rfNode) => {
        const n = impactResult?.nodes.find((x) => x.node_id === rfNode.id) ?? null;
        setSelectedNode(n);
    }, [impactResult]);
    const selectedEvidence = selectedNode
        ? impactResult.edges
            .filter((e) => e.source_id === selectedNode.node_id ||
            e.target_id === selectedNode.node_id)
            .map((e) => ({
            file: e.file,
            line: e.line,
            snippet: e.note,
            evidence_status: e.evidence_status,
        }))
        : [];
    return (_jsxs("div", { style: { padding: 0, height: "100%" }, children: [_jsxs("div", { style: {
                    padding: "14px 20px",
                    borderBottom: "1px solid var(--border)",
                    display: "flex",
                    gap: 12,
                    alignItems: "flex-end",
                    flexWrap: "wrap",
                    background: "var(--surface)",
                }, children: [_jsxs("div", { children: [_jsx("label", { style: { fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }, children: "Mode" }), _jsx("div", { style: { display: "flex", gap: 6 }, children: ["feature", "symbol", "diff"].map((m) => (_jsx("button", { className: `btn ${mode === m ? "btn-primary" : "btn-secondary"}`, style: { padding: "5px 12px", fontSize: 12 }, onClick: () => setMode(m), children: m === "feature" ? "Feature" : m === "symbol" ? "File ID" : "Git Diff" }, m))) })] }), mode === "feature" ? (_jsxs("div", { style: { flex: 1, minWidth: 220 }, children: [_jsx("label", { style: {
                                    fontSize: 12,
                                    fontWeight: 600,
                                    display: "block",
                                    marginBottom: 4,
                                }, children: "Primary feature" }), _jsxs("select", { value: featureId, onChange: (e) => setFeatureId(e.target.value), style: { marginBottom: 0 }, children: [_jsx("option", { value: "", children: "Select a feature\u2026" }), (xray?.features ?? []).map((feature) => (_jsx("option", { value: feature.feature_id, children: feature.name }, feature.feature_id)))] })] })) : mode === "symbol" ? (_jsxs("div", { style: { flex: 1, minWidth: 200 }, children: [_jsx("label", { style: {
                                    fontSize: 12,
                                    fontWeight: 600,
                                    display: "block",
                                    marginBottom: 4,
                                }, children: "Symbol ID" }), _jsx("input", { type: "text", value: symbolId, onChange: (e) => setSymbolId(e.target.value), placeholder: "e.g. app/main.py::create_app", style: { marginBottom: 0 } })] })) : (_jsxs("div", { style: { flex: 1, minWidth: 200 }, children: [_jsx("label", { style: {
                                    fontSize: 12,
                                    fontWeight: 600,
                                    display: "block",
                                    marginBottom: 4,
                                }, children: "Git Diff" }), _jsx("textarea", { value: gitDiff, onChange: (e) => setGitDiff(e.target.value), placeholder: "Paste unified diff here\u2026", rows: 3, style: { marginBottom: 0, resize: "vertical" } })] })), _jsxs("div", { children: [_jsx("label", { style: { fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }, children: "Depth" }), _jsx("div", { style: { display: "flex", gap: 6 }, children: [1, 2, 3].map((d) => (_jsx("button", { className: `btn ${depth === d ? "btn-primary" : "btn-secondary"}`, style: { padding: "5px 10px", fontSize: 12 }, onClick: () => setDepth(d), children: d }, d))) })] }), _jsx("button", { className: "btn btn-primary", onClick: () => trigger(), disabled: isTriggering ||
                            (mode === "feature"
                                ? !featureId
                                : mode === "symbol"
                                    ? !symbolId.trim()
                                    : !gitDiff.trim()), children: isTriggering ? (_jsxs(_Fragment, { children: [_jsx(Spinner, { size: 13 }), " Analysing\u2026"] })) : ("Analyse Impact") })] }), isFetching && (_jsxs("div", { style: { display: "flex", gap: 10, alignItems: "center", padding: 32 }, children: [_jsx(Spinner, {}), " Building impact graph\u2026"] })), impactResult && !isFetching && (_jsxs("div", { style: { display: "flex", height: "calc(100% - 80px)", minHeight: 520 }, children: [_jsxs("div", { style: { flex: 1 }, children: [_jsxs("div", { style: {
                                    padding: "10px 12px",
                                    borderBottom: "1px solid var(--border)",
                                }, children: [_jsxs("div", { style: {
                                            display: "flex",
                                            justifyContent: "space-between",
                                            alignItems: "center",
                                            gap: 12,
                                            marginBottom: 8,
                                        }, children: [_jsxs("div", { children: [_jsx("strong", { style: { fontSize: 13 }, children: "Test plan scope" }), _jsxs("span", { className: "text-muted", style: { marginLeft: 8, fontSize: 12 }, children: [selectedNodeIds.size, " of ", impactResult.nodes.length, " impacted files"] })] }), _jsxs("div", { style: { display: "flex", gap: 6 }, children: [_jsx("button", { className: "btn btn-secondary", style: { padding: "3px 8px", fontSize: 11 }, onClick: () => setSelectedNodeIds(new Set(impactResult.nodes.map((node) => node.node_id))), children: "Select all" }), _jsx("button", { className: "btn btn-secondary", style: { padding: "3px 8px", fontSize: 11 }, onClick: () => setSelectedNodeIds(new Set()), children: "Clear" })] })] }), _jsx("div", { style: {
                                            display: "flex",
                                            flexWrap: "wrap",
                                            gap: 6,
                                            marginBottom: 10,
                                        }, children: impactResult.nodes.map((impactNode) => {
                                            const included = selectedNodeIds.has(impactNode.node_id);
                                            return (_jsx("button", { className: `btn ${included ? "btn-primary" : "btn-secondary"}`, style: { padding: "3px 8px", fontSize: 11 }, title: impactNode.node.path, onClick: () => setSelectedNodeIds((current) => {
                                                    const next = new Set(current);
                                                    if (included)
                                                        next.delete(impactNode.node_id);
                                                    else
                                                        next.add(impactNode.node_id);
                                                    return next;
                                                }), children: impactNode.node.name }, impactNode.node_id));
                                        }) }), _jsx("button", { className: "btn btn-primary", disabled: isPlanning || selectedNodeIds.size === 0, onClick: () => makePlan(), children: isPlanning
                                            ? "Creating test plan…"
                                            : `Create Test Plan for ${selectedNodeIds.size} File${selectedNodeIds.size === 1 ? "" : "s"}` })] }), impactResult.warnings.length > 0 && (_jsx("div", { style: {
                                    margin: 8,
                                    padding: "6px 12px",
                                    background: "#fef9c3",
                                    border: "1px solid #d97706",
                                    borderRadius: "var(--radius)",
                                    fontSize: 12,
                                    color: "#92400e",
                                }, children: impactResult.warnings.join(" · ") })), _jsxs(ReactFlow, { nodes: rfNodes, edges: rfEdges, onNodeClick: handleNodeClick, fitView: true, fitViewOptions: { padding: 0.15 }, children: [_jsx(Background, {}), _jsx(Controls, {}), _jsx(MiniMap, {})] }), (impactResult.external_feature_suggestions?.length ?? 0) > 0 && (_jsxs("div", { style: {
                                    margin: 8,
                                    padding: 10,
                                    border: "1px solid var(--border)",
                                    borderRadius: 6,
                                    fontSize: 12,
                                }, children: [_jsx("strong", { children: "Suggested cross-feature regression scopes:" }), " ", impactResult
                                        .external_feature_suggestions.map((feature) => feature.name)
                                        .join(", ")] }))] }), selectedNode && (_jsxs("div", { style: {
                            width: 300,
                            borderLeft: "1px solid var(--border)",
                            padding: 12,
                            overflowY: "auto",
                        }, children: [_jsx("h3", { style: { marginBottom: 4 }, children: selectedNode.node.name }), _jsx("p", { className: "mono text-muted", style: { marginBottom: 8 }, children: selectedNode.node.path }), _jsxs("p", { style: { fontSize: 12, marginBottom: 8 }, children: [_jsx("strong", { children: "Depth:" }), " ", selectedNode.depth_level] }), selectedNode.existing_tests.length > 0 && (_jsxs("div", { style: { marginBottom: 10 }, children: [_jsx("p", { style: { fontSize: 12, fontWeight: 600, marginBottom: 4 }, children: "Existing tests" }), selectedNode.existing_tests.map((t) => (_jsx("p", { className: "mono", style: { fontSize: 11, color: "var(--accent)" }, children: t }, t)))] })), impactResult.annotations
                                .filter((a) => a.node_id === selectedNode.node_id)
                                .map((a) => (_jsxs("div", { style: {
                                    padding: "8px 10px",
                                    background: "#fef9c3",
                                    border: "1px solid #d97706",
                                    borderRadius: "var(--radius)",
                                    fontSize: 12,
                                    marginBottom: 8,
                                }, children: [_jsxs("strong", { children: ["\u26A0 ", a.hypothesis_label, ":"] }), " ", a.risk] }, a.node_id))), _jsx(EvidencePanel, { refs: selectedEvidence, onClose: () => setSelectedNode(null) })] }))] })), !impactResult && !isFetching && (_jsxs("div", { style: { padding: 32, color: "var(--muted)" }, children: ["Enter a symbol ID or diff above and click ", _jsx("strong", { children: "Analyse Impact" }), "."] }))] }));
}
