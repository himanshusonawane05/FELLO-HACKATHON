import Link from "next/link";
import type { AccountSummary } from "@/types/intelligence";
import IntentMeter from "./IntentMeter";

interface AccountCardProps {
  account: AccountSummary;
}

export default function AccountCard({ account }: AccountCardProps): React.ReactElement {
  return (
    <Link
      href={`/account/${account.account_id}`}
      data-testid="account-card"
      className="block rounded-xl border border-border bg-surface p-5 hover:border-accent transition-all duration-300 group"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-display font-bold text-white group-hover:text-accent transition-colors">
            {account.company_name}
          </h3>
          {account.domain && (
            <p className="text-muted text-xs font-mono mt-0.5">{account.domain}</p>
          )}
        </div>
        <span className="text-xs font-mono text-muted bg-background rounded px-2 py-1">
          {account.industry ?? "—"}
        </span>
      </div>

      {account.intent_score !== undefined && account.intent_score !== null && (
        <IntentMeter score={account.intent_score} stage="" compact />
      )}

      <div className="flex items-center justify-between mt-3">
        <span className="text-xs font-mono text-muted">
          {new Date(account.analyzed_at).toLocaleDateString()}
        </span>
        <span
          className="text-xs font-mono"
          style={{ color: account.confidence_score > 0.6 ? "#00ff88" : "#f59e0b" }}
        >
          {Math.round(account.confidence_score * 100)}% confidence
        </span>
      </div>
    </Link>
  );
}
