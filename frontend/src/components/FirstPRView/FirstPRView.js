import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getStarterTasks } from "@/api/client";
import Spinner from "@/components/Spinner";
export default function FirstPRView({ sessionId, onTaskSelected }) {
    const [selected, setSelected] = useState(null);
    const { data: tasks, isPending, error } = useQuery({
        queryKey: ["starter-tasks", sessionId],
        queryFn: () => getStarterTasks(sessionId),
    });
    if (isPending) {
        return (_jsxs("div", { style: { display: "flex", gap: 10, alignItems: "center", padding: 32 }, children: [_jsx(Spinner, {}), " Loading starter tasks\u2026"] }));
    }
    if (error || !tasks) {
        return (_jsx("div", { style: { padding: 32, color: "var(--muted)" }, children: "Could not load starter tasks. Complete Repository X-Ray first." }));
    }
    return (_jsxs("div", { style: { padding: 24, maxWidth: 700 }, children: [_jsxs("div", { style: { marginBottom: 20 }, children: [_jsx("h2", { style: { marginBottom: 6 }, children: "Your First PR" }), _jsx("p", { className: "text-muted", style: { fontSize: 13 }, children: "Pick a bounded starter task below. RepoDoc will map its impact, propose tests, and help you verify your change before opening a PR." })] }), tasks.length === 0 ? (_jsx("div", { className: "card", style: { color: "var(--muted)", fontSize: 13 }, children: "No starter tasks found for this repository." })) : (_jsx("div", { style: { display: "flex", flexDirection: "column", gap: 12 }, children: tasks.map((task) => {
                    const isSelected = selected?.id === task.id;
                    return (_jsxs("div", { style: {
                            border: `2px solid ${isSelected ? "var(--accent)" : "var(--border)"}`,
                            borderRadius: "var(--radius)",
                            padding: "14px 16px",
                            cursor: "pointer",
                            background: isSelected ? "rgba(59,130,212,0.04)" : "var(--bg)",
                            transition: "border-color 0.15s",
                        }, onClick: () => setSelected(isSelected ? null : task), children: [_jsxs("div", { style: {
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "flex-start",
                                    marginBottom: 6,
                                }, children: [_jsx("strong", { style: { fontSize: 14 }, children: task.title }), _jsxs("span", { style: {
                                            fontSize: 11,
                                            color: "var(--muted)",
                                            background: "var(--surface)",
                                            border: "1px solid var(--border)",
                                            padding: "2px 8px",
                                            borderRadius: 10,
                                            whiteSpace: "nowrap",
                                        }, children: ["depth ", task.recommended_impact_depth] })] }), _jsx("p", { style: {
                                    fontSize: 13,
                                    color: "var(--text)",
                                    marginBottom: 8,
                                    lineHeight: 1.5,
                                }, children: task.description }), _jsxs("p", { className: "mono text-muted", style: { fontSize: 11 }, children: [task.target_file, ":", task.target_line] }), isSelected && (_jsx("div", { style: { marginTop: 12 }, children: _jsx("button", { className: "btn btn-primary", onClick: (e) => {
                                        e.stopPropagation();
                                        onTaskSelected?.(task);
                                    }, children: "Start with this task \u2192" }) }))] }, task.id));
                }) }))] }));
}
