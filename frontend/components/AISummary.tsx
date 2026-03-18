interface AISummaryProps {
  summary: string;
}

export default function AISummary({ summary }: AISummaryProps): React.ReactElement {
  if (!summary) {
    return (
      <div data-testid="ai-summary" className="rounded-xl border border-border bg-surface p-5">
        <h3 className="font-display font-bold text-white text-sm mb-2">AI Summary</h3>
        <p className="text-muted text-xs font-mono">No summary generated.</p>
      </div>
    );
  }

  return (
    <div data-testid="ai-summary" className="rounded-xl border border-accent/20 bg-accent/5 p-5">
      <h3 className="font-display font-bold text-accent text-sm mb-3">AI Summary</h3>
      <p className="text-white text-sm leading-relaxed">{summary}</p>
    </div>
  );
}
