"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AccountCard from "@/components/AccountCard";
import AnalysisForm from "@/components/AnalysisForm";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import PipelineProgress from "@/components/PipelineProgress";
import VisitorScenarios from "@/components/VisitorScenarios";
import { useAccountAnalysis } from "@/hooks/useAccountAnalysis";
import { api } from "@/lib/api";
import type { AccountSummary, CompanyAnalysisRequest, VisitorAnalysisRequest } from "@/types/intelligence";

type DashboardTab = "dashboard" | "scenarios";

function isCompanyRequest(
  data: VisitorAnalysisRequest | CompanyAnalysisRequest
): data is CompanyAnalysisRequest {
  return "company_name" in data;
}

export default function DashboardPage(): React.ReactElement {
  const router = useRouter();
  const { submit, isSubmitting, isLoading, result, error, pipelineStep, pipelineProgress, reset } =
    useAccountAnalysis();

  const [activeTab, setActiveTab] = useState<DashboardTab>("dashboard");
  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [pendingCompany, setPendingCompany] = useState<string | null>(null);

  // Load recent accounts on mount
  useEffect(() => {
    api
      .listAccounts()
      .then((data) => setAccounts(data.accounts))
      .catch(() => setAccounts([]))
      .finally(() => setAccountsLoading(false));
  }, []);

  // Navigate to account detail when analysis completes
  useEffect(() => {
    if (result) {
      // Add to recent accounts list
      setAccounts((prev) => {
        const exists = prev.some((a) => a.account_id === result.account_id);
        if (exists) return prev;
        const summary: AccountSummary = {
          success: true,
          account_id: result.account_id,
          company_name: result.company_name,
          domain: result.domain,
          industry: result.industry,
          intent_score: result.intent_score,
          confidence_score: result.confidence_score,
          analyzed_at: result.analyzed_at,
        };
        return [summary, ...prev.slice(0, 9)];
      });
      // Navigate to the full account detail page
      router.push(`/account/${result.account_id}`);
    }
  }, [result, router]);

  const handleSubmit = async (
    data: VisitorAnalysisRequest | CompanyAnalysisRequest
  ): Promise<void> => {
    if (isCompanyRequest(data)) {
      setPendingCompany(data.company_name);
    } else {
      setPendingCompany("Visitor Signal");
    }
    await submit(data);
  };

  const handleReset = (): void => {
    setPendingCompany(null);
    reset();
  };

  const isPipelineRunning = isLoading && !isSubmitting;

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section>
        <div className="flex items-center gap-2 mb-2">
          <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
          <span className="text-[10px] font-mono text-accent uppercase tracking-widest">
            AI Pipeline Active
          </span>
        </div>
        <h1 className="font-display font-extrabold text-3xl text-white mb-1">
          Account Intelligence
        </h1>
        <p className="text-muted text-sm font-mono max-w-xl">
          Convert visitor signals and company names into structured sales intelligence — powered
          by a multi-agent AI pipeline.
        </p>
      </section>

      {/* Tab switcher */}
      <div className="flex gap-2 border-b border-border pb-0">
        {(
          [
            { id: "dashboard", label: "Dashboard" },
            { id: "scenarios", label: "Visitor Scenarios" },
          ] as { id: DashboardTab; label: string }[]
        ).map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`px-5 py-2.5 text-sm font-mono font-medium border-b-2 transition-all -mb-px ${
              activeTab === id
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-white"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Visitor Scenarios tab */}
      {activeTab === "scenarios" && <VisitorScenarios />}

      {/* Dashboard tab content */}
      {activeTab === "dashboard" && (
        <>
      {/* Analysis form (hidden during pipeline run) */}
      {!isPipelineRunning && (
        <AnalysisForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      )}

      {/* Pipeline progress */}
      {isPipelineRunning && (
        <div className="space-y-4">
          <PipelineProgress
            step={pipelineStep}
            progress={pipelineProgress}
            companyName={pendingCompany ?? undefined}
          />
          <button
            onClick={handleReset}
            className="text-xs font-mono text-muted hover:text-white transition-colors"
          >
            ← Cancel and start over
          </button>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 flex items-start justify-between gap-4">
          <div>
            <p className="text-red-400 text-sm font-mono font-semibold">Analysis failed</p>
            <p className="text-red-400/70 text-xs font-mono mt-0.5">{error}</p>
          </div>
          <button
            onClick={handleReset}
            className="text-red-400 text-xs font-mono hover:text-red-300 transition-colors shrink-0"
          >
            Retry →
          </button>
        </div>
      )}

      {/* Recent accounts */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display font-bold text-xl text-white">Recent Accounts</h2>
          <span className="text-xs font-mono text-muted">{accounts.length} analyzed</span>
        </div>

        {accountsLoading ? (
          <LoadingSkeleton count={3} />
        ) : accounts.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-muted font-mono text-sm">No accounts analyzed yet.</p>
            <p className="text-muted/60 font-mono text-xs mt-1">
              Submit a company above to generate your first intelligence report.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {accounts.map((account) => (
              <AccountCard key={account.account_id} account={account} />
            ))}
          </div>
        )}
      </section>

      {/* How it works (shown when no pipeline is running) */}
      {!isPipelineRunning && (
        <section className="border-t border-border pt-8">
          <h3 className="font-display font-bold text-sm text-white mb-4">How the pipeline works</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { step: "01", label: "IP / Name Lookup", color: "#00ff88" },
              { step: "02", label: "Company Enrichment", color: "#34d399" },
              { step: "03", label: "Persona Inference", color: "#60a5fa" },
              { step: "04", label: "Intent Scoring", color: "#a78bfa" },
              { step: "05", label: "Playbook Generation", color: "#f59e0b" },
              { step: "06", label: "Intelligence Report", color: "#f472b6" },
            ].map(({ step, label, color }) => (
              <div
                key={step}
                className="rounded-lg border border-border bg-surface p-3 flex flex-col gap-2"
              >
                <span className="font-mono text-[10px] font-bold" style={{ color }}>
                  {step}
                </span>
                <span className="text-white text-xs font-display font-semibold leading-tight">
                  {label}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
        </>
      )}
    </div>
  );
}
