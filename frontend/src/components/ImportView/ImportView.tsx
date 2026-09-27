import { useState, type FormEvent } from "react";
import { useCreateSession } from "@/hooks/useSession";
import Spinner from "@/components/Spinner";

interface ImportViewProps {
  onSessionCreated: (sessionId: string) => void;
}

export default function ImportView({ onSessionCreated }: ImportViewProps) {
  const [repoPath, setRepoPath] = useState("");
  const [architecturePath, setArchitecturePath] = useState("");
  const { mutate, isPending, error } = useCreateSession();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const path = repoPath.trim();
    const wikiPath = architecturePath.trim();
    if (!path || !wikiPath) return;
    mutate(
      { repo_path: path, architecture_path: wikiPath },
      { onSuccess: (session) => onSessionCreated(session.session_id) },
    );
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--surface)",
      }}
    >
      <div
        style={{
          background: "var(--bg)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius)",
          padding: 32,
          maxWidth: 500,
          width: "100%",
          boxShadow: "var(--shadow)",
        }}
      >
        {/* Logo / heading */}
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ marginBottom: 4 }}>
            <span style={{ color: "var(--accent)" }}>Repo</span>Doc
          </h1>
          <p className="text-muted" style={{ fontSize: 13 }}>
            Understand, verify, and contribute to any codebase — evidence first.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <label
            htmlFor="repo-path"
            style={{ display: "block", marginBottom: 6, fontWeight: 500 }}
          >
            Repository path
          </label>
          <input
            id="repo-path"
            type="text"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            placeholder="/absolute/path/to/repo"
            style={{ marginBottom: 16 }}
            autoFocus
          />

          <label
            htmlFor="architecture-path"
            style={{ display: "block", marginBottom: 6, fontWeight: 500 }}
          >
            Feature wiki directory
          </label>
          <input
            id="architecture-path"
            type="text"
            value={architecturePath}
            onChange={(e) => setArchitecturePath(e.target.value)}
            placeholder="dayate_wiki or /absolute/path/to/wiki"
            style={{ marginBottom: 16 }}
          />

          {error && (
            <p className="text-danger" style={{ fontSize: 13, marginBottom: 12 }}>
              {error.message}
            </p>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isPending || !repoPath.trim() || !architecturePath.trim()}
            style={{ width: "100%", justifyContent: "center" }}
          >
            {isPending ? (
              <>
                <Spinner size={14} label="Analysing repository" /> Analysing repository…
              </>
            ) : (
              "Analyse Repository"
            )}
          </button>
        </form>

        <p
          className="text-muted"
          style={{ fontSize: 12, marginTop: 16, lineHeight: 1.5 }}
        >
          RepoDoc clones the repository into a read-only sandbox. Your original files
          are never modified.
        </p>
      </div>
    </div>
  );
}
