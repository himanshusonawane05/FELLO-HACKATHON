"use client";

interface PipelineProgressProps {
  step: string | null;
  progress: number;
  companyName?: string;
}

const STAGE_LABELS = [
  "Identifying company",
  "Enriching data",
  "Inferring persona",
  "Scoring intent",
  "Building playbook",
  "Finalizing report",
];

export default function PipelineProgress({
  step,
  progress,
  companyName,
}: PipelineProgressProps): React.ReactElement {
  const activeStageIndex = Math.min(
    Math.floor((progress / 100) * STAGE_LABELS.length),
    STAGE_LABELS.length - 1
  );

  return (
    <div data-testid="pipeline-progress" className="rounded-xl border border-accent/20 bg-surface p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-display font-bold text-white text-sm">
            Running Analysis Pipeline
          </h3>
          {companyName && (
            <p className="text-muted text-xs font-mono mt-0.5">
              Target: <span className="text-accent">{companyName}</span>
            </p>
          )}
        </div>
        <span className="font-mono text-accent text-sm font-semibold tabular-nums">
          {progress}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 rounded-full bg-background overflow-hidden">
        <div
          data-testid="pipeline-progress-bar"
          className="h-full rounded-full animate-progress"
          style={{
            width: `${progress}%`,
            backgroundColor: progress < 50 ? "#f59e0b" : "#00ff88",
          }}
        />
      </div>

      {/* Current step message */}
      <div className="flex items-center gap-2 min-h-[20px]">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
        <span data-testid="pipeline-step" className="text-xs font-mono text-white/80">
          {step ?? "Initializing..."}
        </span>
      </div>

      {/* Stage dots */}
      <div className="flex items-center gap-1.5 pt-1">
        {STAGE_LABELS.map((label, idx) => {
          const isDone = idx < activeStageIndex;
          const isActive = idx === activeStageIndex;
          return (
            <div key={label} className="flex flex-col items-center gap-1 flex-1">
              <div
                className="h-1.5 w-full rounded-full transition-all duration-500"
                style={{
                  backgroundColor: isDone
                    ? "#00ff88"
                    : isActive
                    ? "#f59e0b"
                    : "#222222",
                  opacity: isDone || isActive ? 1 : 0.4,
                }}
              />
              <span
                className="text-[9px] font-mono text-center leading-tight hidden sm:block"
                style={{
                  color: isDone ? "#00ff88" : isActive ? "#f59e0b" : "#444",
                }}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
