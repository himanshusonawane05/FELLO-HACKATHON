interface IntentMeterProps {
  score: number;
  stage: string;
  compact?: boolean;
}

function getColor(score: number): string {
  if (score < 4) return "#ef4444";
  if (score <= 7) return "#f59e0b";
  return "#00ff88";
}

export default function IntentMeter({ score, stage, compact = false }: IntentMeterProps): React.ReactElement {
  const pct = Math.round((score / 10) * 100);
  const color = getColor(score);

  return (
    <div data-testid="intent-meter" className={compact ? "" : "rounded-xl border border-border bg-surface p-5"}>
      {!compact && (
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display font-bold text-white text-sm">Intent Score</h3>
          <span data-testid="intent-stage" className="text-xs font-mono text-muted">{stage}</span>
        </div>
      )}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 rounded-full bg-background overflow-hidden">
          <div
            className="h-full rounded-full animate-progress"
            style={{ width: `${pct}%`, backgroundColor: color }}
          />
        </div>
        <span
          data-testid="intent-score"
          className="font-mono text-sm font-semibold tabular-nums w-8 text-right"
          style={{ color }}
        >
          {score.toFixed(1)}
        </span>
      </div>
    </div>
  );
}
