
interface SpinnerProps {
  size?: number;
  label?: string;
}

export default function Spinner({ size = 20, label = "Loading…" }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label={label}
      style={{
        display: "inline-block",
        width: size,
        height: size,
        border: `2px solid var(--border)`,
        borderTopColor: "var(--accent)",
        borderRadius: "50%",
        animation: "spin 0.7s linear infinite",
      }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </span>
  );
}
