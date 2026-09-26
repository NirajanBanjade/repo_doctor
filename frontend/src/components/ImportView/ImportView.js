import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from "react";
import { useCreateSession } from "@/hooks/useSession";
import Spinner from "@/components/Spinner";
export default function ImportView({ onSessionCreated }) {
    const [repoPath, setRepoPath] = useState("");
    const { mutate, isPending, error } = useCreateSession();
    const handleSubmit = (e) => {
        e.preventDefault();
        const path = repoPath.trim();
        if (!path)
            return;
        mutate({ repo_path: path }, { onSuccess: (session) => onSessionCreated(session.session_id) });
    };
    return (_jsx("div", { style: {
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--surface)",
        }, children: _jsxs("div", { style: {
                background: "var(--bg)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                padding: 32,
                maxWidth: 500,
                width: "100%",
                boxShadow: "var(--shadow)",
            }, children: [_jsxs("div", { style: { marginBottom: 24 }, children: [_jsxs("h1", { style: { marginBottom: 4 }, children: [_jsx("span", { style: { color: "var(--accent)" }, children: "Repo" }), "Doc"] }), _jsx("p", { className: "text-muted", style: { fontSize: 13 }, children: "Understand, verify, and contribute to any codebase \u2014 evidence first." })] }), _jsxs("form", { onSubmit: handleSubmit, children: [_jsx("label", { htmlFor: "repo-path", style: { display: "block", marginBottom: 6, fontWeight: 500 }, children: "Repository path" }), _jsx("input", { id: "repo-path", type: "text", value: repoPath, onChange: (e) => setRepoPath(e.target.value), placeholder: "/absolute/path/to/repo", style: { marginBottom: 16 }, autoFocus: true }), error && (_jsx("p", { className: "text-danger", style: { fontSize: 13, marginBottom: 12 }, children: error.message })), _jsx("button", { type: "submit", className: "btn btn-primary", disabled: isPending || !repoPath.trim(), style: { width: "100%", justifyContent: "center" }, children: isPending ? (_jsxs(_Fragment, { children: [_jsx(Spinner, { size: 14, label: "Creating session" }), " Creating session\u2026"] })) : ("Analyse Repository") })] }), _jsx("p", { className: "text-muted", style: { fontSize: 12, marginTop: 16, lineHeight: 1.5 }, children: "RepoDoc clones the repository into a read-only sandbox. Your original files are never modified." })] }) }));
}
