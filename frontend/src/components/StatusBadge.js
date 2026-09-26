import { jsx as _jsx } from "react/jsx-runtime";
const STATUS_LABELS = {
    created: "Created",
    importing: "Importing…",
    xray_running: "X-Ray Running…",
    xray_complete: "X-Ray Complete",
    environment_running: "Env Running…",
    environment_complete: "Env Ready",
    impact_running: "Impact Running…",
    impact_complete: "Impact Complete",
    tests_running: "Tests Running…",
    tests_complete: "Tests Complete",
    verified: "Verified ✓",
    error: "Error",
};
const STATUS_COLORS = {
    created: "#57606a",
    importing: "#d97706",
    xray_running: "#d97706",
    xray_complete: "#3b82d4",
    environment_running: "#d97706",
    environment_complete: "#16a34a",
    impact_running: "#d97706",
    impact_complete: "#3b82d4",
    tests_running: "#d97706",
    tests_complete: "#3b82d4",
    verified: "#16a34a",
    error: "#dc2626",
};
export default function StatusBadge({ status }) {
    return (_jsx("span", { style: {
            display: "inline-block",
            padding: "2px 10px",
            borderRadius: 12,
            fontSize: 12,
            fontWeight: 600,
            background: STATUS_COLORS[status] + "1a",
            color: STATUS_COLORS[status],
            border: `1px solid ${STATUS_COLORS[status]}44`,
            whiteSpace: "nowrap",
        }, children: STATUS_LABELS[status] }));
}
