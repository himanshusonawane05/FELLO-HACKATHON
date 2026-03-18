import type { RecommendedActionSchema } from "@/types/intelligence";

interface SalesPlaybookProps {
  actions: RecommendedActionSchema[];
  talkingPoints: string[];
  outreachTemplate: string | null;
  priority: string;
}

const PRIORITY_STYLES: Record<string, string> = {
  HIGH: "border-red-500/40 bg-red-500/5",
  MEDIUM: "border-amber-500/40 bg-amber-500/5",
  LOW: "border-border bg-surface",
};

export default function SalesPlaybook({
  actions,
  talkingPoints,
  outreachTemplate,
  priority,
}: SalesPlaybookProps): React.ReactElement {
  return (
    <div data-testid="sales-playbook" className={`rounded-xl border p-5 space-y-4 ${PRIORITY_STYLES[priority] ?? PRIORITY_STYLES.LOW}`}>
      <div className="flex items-center justify-between">
        <h3 className="font-display font-bold text-white text-sm">Sales Playbook</h3>
        <span
          data-testid="playbook-priority"
          className={`text-xs font-mono px-2 py-0.5 rounded ${
            priority === "HIGH"
              ? "text-red-400 bg-red-500/10"
              : priority === "MEDIUM"
              ? "text-amber-400 bg-amber-500/10"
              : "text-muted bg-background"
          }`}
        >
          {priority}
        </span>
      </div>

      {actions.length > 0 && (
        <div>
          <p className="text-muted text-xs font-mono mb-2">Recommended Actions</p>
          <ul className="space-y-2">
            {actions.map((action, idx) => (
              <li key={idx} className="text-sm">
                <span className="text-white font-semibold">{action.action}</span>
                <span className="text-muted text-xs font-mono block">{action.rationale}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {talkingPoints.length > 0 && (
        <div>
          <p className="text-muted text-xs font-mono mb-2">Talking Points</p>
          <ul className="list-disc list-inside space-y-1">
            {talkingPoints.map((point, idx) => (
              <li key={idx} className="text-sm text-white">
                {point}
              </li>
            ))}
          </ul>
        </div>
      )}

      {outreachTemplate && (
        <div>
          <p className="text-muted text-xs font-mono mb-2">Outreach Template</p>
          <pre className="whitespace-pre-wrap text-xs text-white font-mono bg-background rounded-lg p-3 leading-relaxed">
            {outreachTemplate}
          </pre>
        </div>
      )}
    </div>
  );
}
