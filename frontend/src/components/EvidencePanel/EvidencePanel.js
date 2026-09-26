import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
const STATUS_STYLE = {
    confirmed_static: { color: "var(--success)", fontWeight: 600 },
    observed_test: { color: "var(--accent)", fontWeight: 600 },
    inferred: { color: "var(--warning)", fontWeight: 600 },
};
const STATUS_LABEL = {
    confirmed_static: "static",
    observed_test: "test",
    inferred: "inferred",
};
export default function EvidencePanel({ refs, onClose }) {
    return (_jsxs("aside", { style: {
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            padding: 16,
            minWidth: 280,
            maxWidth: 360,
        }, children: [_jsxs("div", { style: {
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 10,
                }, children: [_jsx("h3", { style: { margin: 0 }, children: "Evidence" }), onClose && (_jsx("button", { className: "btn btn-secondary", onClick: onClose, style: { padding: "2px 8px", fontSize: 12 }, children: "\u2715" }))] }), refs.length === 0 ? (_jsx("p", { className: "text-muted", style: { fontSize: 12 }, children: "No evidence references." })) : (_jsx("ul", { style: { listStyle: "none", padding: 0, margin: 0 }, children: refs.map((ref, i) => (_jsxs("li", { style: {
                        marginBottom: 10,
                        paddingBottom: 10,
                        borderBottom: i < refs.length - 1
                            ? "1px solid var(--border)"
                            : "none",
                    }, children: [_jsxs("div", { className: "mono", style: { display: "flex", gap: 6, alignItems: "baseline" }, children: [_jsxs("span", { style: { color: "var(--text)" }, children: [ref.file, ":", ref.line] }), _jsxs("span", { style: STATUS_STYLE[ref.evidence_status], children: ["[", STATUS_LABEL[ref.evidence_status], "]"] })] }), ref.snippet && (_jsx("pre", { className: "mono", style: {
                                marginTop: 4,
                                padding: "6px 8px",
                                background: "var(--bg)",
                                border: "1px solid var(--border)",
                                borderRadius: "var(--radius)",
                                overflowX: "auto",
                                whiteSpace: "pre-wrap",
                                wordBreak: "break-all",
                            }, children: ref.snippet }))] }, i))) }))] }));
}
