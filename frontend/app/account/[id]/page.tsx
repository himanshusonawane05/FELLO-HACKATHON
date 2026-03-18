"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import AISummary from "@/components/AISummary";
import CompanyProfileCard from "@/components/CompanyProfileCard";
import IntentMeter from "@/components/IntentMeter";
import LeadershipList from "@/components/LeadershipList";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import PersonaBadge from "@/components/PersonaBadge";
import SalesPlaybook from "@/components/SalesPlaybook";
import SignalsFeed from "@/components/SignalsFeed";
import TechStackGrid from "@/components/TechStackGrid";
import { useAccountAnalysis } from "@/hooks/useAccountAnalysis";

export default function AccountDetailPage(): React.ReactElement {
  const params = useParams<{ id: string }>();
  const { result, isLoading, error } = useAccountAnalysis(params.id);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 rounded-lg bg-surface border border-border animate-pulse" />
        <LoadingSkeleton count={2} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <LoadingSkeleton count={2} />
          </div>
          <div className="space-y-6">
            <LoadingSkeleton count={2} />
          </div>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="space-y-4">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs font-mono text-muted hover:text-white transition-colors"
        >
          ← Dashboard
        </Link>
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-6 text-red-400 font-mono">
          {error ?? "Account not found."}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back nav */}
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-xs font-mono text-muted hover:text-accent transition-colors"
      >
        ← Dashboard
      </Link>

      {/* Account header */}
      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="font-display font-extrabold text-3xl text-white">
              {result.company_name}
            </h1>
            {result.playbook_priority && (
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                  result.playbook_priority === "HIGH"
                    ? "border-red-500/40 text-red-400 bg-red-500/10"
                    : result.playbook_priority === "MEDIUM"
                    ? "border-amber-500/40 text-amber-400 bg-amber-500/10"
                    : "border-border text-muted bg-surface"
                }`}
              >
                {result.playbook_priority} PRIORITY
              </span>
            )}
          </div>
          {result.domain && (
            <a
              href={`https://${result.domain}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent text-sm font-mono hover:underline"
            >
              {result.domain} ↗
            </a>
          )}
          <p className="text-muted text-xs font-mono mt-2">
            Analyzed {new Date(result.analyzed_at).toLocaleString()} ·{" "}
            <span style={{ color: result.confidence_score > 0.8 ? "#00ff88" : "#f59e0b" }}>
              {Math.round(result.confidence_score * 100)}% overall confidence
            </span>
          </p>
        </div>
        {result.likely_role && (
          <PersonaBadge
            role={result.likely_role}
            seniority={result.seniority_level ?? "UNKNOWN"}
            confidence={result.persona_confidence ?? 0}
          />
        )}
      </header>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column — primary */}
        <div className="lg:col-span-2 space-y-6">
          <CompanyProfileCard intelligence={result} />

          {result.intent_score !== null && result.intent_score !== undefined && (
            <IntentMeter
              score={result.intent_score}
              stage={result.intent_stage ?? "AWARENESS"}
            />
          )}

          <AISummary summary={result.ai_summary} />
        </div>

        {/* Right column — signals */}
        <div className="space-y-6">
          <TechStackGrid technologies={result.technologies} />
          <SignalsFeed signals={result.business_signals} />
        </div>
      </div>

      {/* Bottom row — action-oriented */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LeadershipList leaders={result.leaders} />
        <SalesPlaybook
          actions={result.recommended_actions}
          talkingPoints={result.talking_points}
          outreachTemplate={result.outreach_template ?? null}
          priority={result.playbook_priority ?? "MEDIUM"}
        />
      </div>
    </div>
  );
}
