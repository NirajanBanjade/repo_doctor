import { jsx as _jsx } from "react/jsx-runtime";
export default function Spinner({ size = 20, label = "Loading…" }) {
    return (_jsx("span", { role: "status", "aria-label": label, style: {
            display: "inline-block",
            width: size,
            height: size,
            border: `2px solid var(--border)`,
            borderTopColor: "var(--accent)",
            borderRadius: "50%",
            animation: "spin 0.7s linear infinite",
        }, children: _jsx("style", { children: `@keyframes spin { to { transform: rotate(360deg); } }` }) }));
}
