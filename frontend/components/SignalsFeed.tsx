import type { SignalSchema } from "@/types/intelligence";

interface SignalsFeedProps {
  signals: SignalSchema[];
}

const SIGNAL_COLORS: Record<string, string> = {
  HIRING: "#00ff88",
  FUNDING: "#a78bfa",
  EXPANSION: "#60a5fa",
  PRODUCT_LAUNCH: "#f59e0b",
  PARTNERSHIP: "#34d399",
  LEADERSHIP_CHANGE: "#f472b6",
  OTHER: "#6b7280",
};

export default function SignalsFeed({ signals }: SignalsFeedProps): React.ReactElement {
  return (
    <div data-testid="signals-feed" className="rounded-xl border border-border bg-surface p-5">
      <h3 className="font-display font-bold text-white text-sm mb-3">Business Signals</h3>
      {signals.length === 0 ? (
        <p className="text-muted text-xs font-mono">No signals detected.</p>
      ) : (
        <ul className="space-y-3">
          {signals.map((signal, idx) => (
            <li key={idx} className="flex gap-3">
              <span
                className="mt-1 h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: SIGNAL_COLORS[signal.signal_type] ?? "#6b7280" }}
              />
              <div>
                <span className="text-white text-xs font-semibold">{signal.title}</span>
                <p className="text-muted text-xs font-mono mt-0.5">{signal.description}</p>
                {signal.source_url && (
                  <a
                    href={signal.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent text-[10px] font-mono hover:underline"
                  >
                    Source ↗
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
