import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getStarterTasks } from "@/api/client";
import Spinner from "@/components/Spinner";
import type { StarterTask } from "@/types";

interface Props {
  sessionId: string;
  onTaskSelected?: (task: StarterTask) => void;
}

export default function FirstPRView({ sessionId, onTaskSelected }: Props) {
  const [selected, setSelected] = useState<StarterTask | null>(null);

  const { data: tasks, isPending, error } = useQuery({
    queryKey: ["starter-tasks", sessionId],
    queryFn: () => getStarterTasks(sessionId),
  });

  if (isPending) {
    return (
      <div style={{ display: "flex", gap: 10, alignItems: "center", padding: 32 }}>
        <Spinner /> Loading starter tasks…
      </div>
    );
  }

  if (error || !tasks) {
    return (
      <div style={{ padding: 32, color: "var(--muted)" }}>
        Could not load starter tasks. Complete Repository X-Ray first.
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 700 }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ marginBottom: 6 }}>Your First PR</h2>
        <p className="text-muted" style={{ fontSize: 13 }}>
          Pick a bounded starter task below. RepoDoc will map its impact,
          propose tests, and help you verify your change before opening a PR.
        </p>
      </div>

      {tasks.length === 0 ? (
        <div
          className="card"
          style={{ color: "var(--muted)", fontSize: 13 }}
        >
          No starter tasks found for this repository.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {tasks.map((task) => {
            const isSelected = selected?.id === task.id;
            return (
              <div
                key={task.id}
                style={{
                  border: `2px solid ${isSelected ? "var(--accent)" : "var(--border)"}`,
                  borderRadius: "var(--radius)",
                  padding: "14px 16px",
                  cursor: "pointer",
                  background: isSelected ? "rgba(59,130,212,0.04)" : "var(--bg)",
                  transition: "border-color 0.15s",
                }}
                onClick={() => setSelected(isSelected ? null : task)}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: 6,
                  }}
                >
                  <strong style={{ fontSize: 14 }}>{task.title}</strong>
                  <span
                    style={{
                      fontSize: 11,
                      color: "var(--muted)",
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      padding: "2px 8px",
                      borderRadius: 10,
                      whiteSpace: "nowrap",
                    }}
                  >
                    depth {task.recommended_impact_depth}
                  </span>
                </div>

                <p
                  style={{
                    fontSize: 13,
                    color: "var(--text)",
                    marginBottom: 8,
                    lineHeight: 1.5,
                  }}
                >
                  {task.description}
                </p>

                <p
                  className="mono text-muted"
                  style={{ fontSize: 11 }}
                >
                  {task.target_file}:{task.target_line}
                </p>

                {isSelected && (
                  <div style={{ marginTop: 12 }}>
                    <button
                      className="btn btn-primary"
                      onClick={(e) => {
                        e.stopPropagation();
                        onTaskSelected?.(task);
                      }}
                    >
                      Start with this task →
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
