import type { AccountIntelligenceResponse } from "@/types/intelligence";

interface CompanyProfileCardProps {
  intelligence: AccountIntelligenceResponse;
}

export default function CompanyProfileCard({ intelligence }: CompanyProfileCardProps): React.ReactElement {
  const fields: { label: string; value: string | undefined | null }[] = [
    { label: "Industry", value: intelligence.industry },
    { label: "Size", value: intelligence.company_size },
    { label: "HQ", value: intelligence.headquarters },
    { label: "Revenue", value: intelligence.annual_revenue_range },
  ];

  return (
    <div data-testid="company-profile" className="rounded-xl border border-border bg-surface p-5">
      <h2 className="font-display font-bold text-white mb-1">
        {intelligence.company_name}
      </h2>
      {intelligence.domain && (
        <a
          href={`https://${intelligence.domain}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent text-xs font-mono hover:underline"
        >
          {intelligence.domain}
        </a>
      )}
      {intelligence.description && (
        <p className="text-text-dim text-sm mt-3 leading-relaxed">
          {intelligence.description}
        </p>
      )}
      <div className="grid grid-cols-2 gap-3 mt-4">
        {fields.map(({ label, value }) =>
          value ? (
            <div key={label}>
              <span className="text-muted text-xs font-mono block">{label}</span>
              <span className="text-white text-sm">{value}</span>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}
