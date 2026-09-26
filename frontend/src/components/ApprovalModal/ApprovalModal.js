import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef } from "react";
import ReactDOM from "react-dom";
export default function ApprovalModal({ title, message, confirmLabel = "Confirm", cancelLabel = "Cancel", onConfirm, onCancel, isLoading = false, }) {
    const overlayRef = useRef(null);
    // Close on Escape key
    useEffect(() => {
        const handler = (e) => {
            if (e.key === "Escape")
                onCancel();
        };
        document.addEventListener("keydown", handler);
        return () => document.removeEventListener("keydown", handler);
    }, [onCancel]);
    return ReactDOM.createPortal(_jsx("div", { ref: overlayRef, role: "dialog", "aria-modal": "true", "aria-labelledby": "approval-modal-title", style: {
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
        }, onClick: (e) => {
            if (e.target === overlayRef.current)
                onCancel();
        }, children: _jsxs("div", { style: {
                background: "var(--bg)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                padding: 24,
                maxWidth: 440,
                width: "100%",
                boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
            }, children: [_jsx("h2", { id: "approval-modal-title", style: { marginBottom: 10 }, children: title }), _jsx("p", { style: {
                        color: "var(--muted)",
                        marginBottom: 20,
                        lineHeight: 1.6,
                    }, children: message }), _jsxs("div", { style: { display: "flex", gap: 10, justifyContent: "flex-end" }, children: [_jsx("button", { className: "btn btn-secondary", onClick: onCancel, disabled: isLoading, children: cancelLabel }), _jsx("button", { className: "btn btn-primary", onClick: onConfirm, disabled: isLoading, children: isLoading ? "Working…" : confirmLabel })] })] }) }), document.body);
}
