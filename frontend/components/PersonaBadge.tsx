interface PersonaBadgeProps {
  role: string;
  seniority: string;
  confidence: number;
}

export default function PersonaBadge({ role, seniority, confidence }: PersonaBadgeProps): React.ReactElement {
  const isLowConfidence = confidence < 0.5;

  return (
    <div
      data-testid="persona-badge"
      className={`inline-flex flex-col items-end gap-1 rounded-lg border px-3 py-2 ${
        isLowConfidence ? "border-border" : "border-accent/40 bg-accent/5"
      }`}
    >
      <span
        className={`text-xs font-display font-semibold ${
          isLowConfidence ? "text-muted" : "text-accent"
        }`}
      >
        {role}
      </span>
      <span className="text-xs font-mono text-muted">
        {seniority.replace("_", " ")} · {Math.round(confidence * 100)}%
      </span>
    </div>
  );
}
