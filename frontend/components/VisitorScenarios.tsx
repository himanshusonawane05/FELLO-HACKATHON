"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PipelineProgress from "@/components/PipelineProgress";
import { useAccountAnalysis } from "@/hooks/useAccountAnalysis";
import type { VisitorAnalysisRequest } from "@/types/intelligence";

interface Scenario {
  id: string;
  label: string;
  tag: string;
  tagColor: string;
  description: string;
  signal: string;
  data: VisitorAnalysisRequest;
}

const SCENARIOS: Scenario[] = [
  {
    id: "high-intent",
    label: "High-Intent Buyer",
    tag: "HOT LEAD",
    tagColor: "#00ff88",
    description:
      "Pricing + demo pages, 3 visits this week, referred from a competitor comparison site.",
    signal: "Strong purchase signals",
    data: {
      visitor_id: "visitor_high_001",
      ip_address: "34.201.45.12",
      pages_visited: ["/pricing", "/demo", "/enterprise", "/case-studies", "/roi-calculator"],
      time_on_site_seconds: 342,
      visit_count: 3,
      referral_source: "paid_search",
      device_type: "desktop",
    },
  },
  {
    id: "technical-eval",
    label: "Technical Evaluator",
    tag: "EVALUATION",
    tagColor: "#60a5fa",
    description:
      "Deep dive into docs, API references, and security pages. Likely an engineer vetting the product.",
    signal: "Technical due diligence",
    data: {
      visitor_id: "visitor_tech_002",
      ip_address: "52.86.112.77",
      pages_visited: ["/docs", "/api-reference", "/security", "/integrations", "/changelog"],
      time_on_site_seconds: 487,
      visit_count: 5,
      referral_source: "organic_search",
      device_type: "desktop",
    },
  },
  {
    id: "research",
    label: "Early Researcher",
    tag: "AWARENESS",
    tagColor: "#a78bfa",
    description:
      "Blog posts and about page only. First visit, mobile device — likely top-of-funnel discovery.",
    signal: "Early awareness stage",
    data: {
      visitor_id: "visitor_research_003",
      ip_address: "18.144.23.91",
      pages_visited: ["/blog/what-is-account-intelligence", "/about", "/features"],
      time_on_site_seconds: 95,
      visit_count: 1,
      referral_source: "social",
      device_type: "mobile",
    },
  },
  {
    id: "low-signal",
    label: "Low-Signal Visitor",
    tag: "COLD",
    tagColor: "#6b7280",
    description:
      "Single page visit, very short session. Could be a bot, casual browser, or wrong audience.",
    signal: "Minimal engagement",
    data: {
      visitor_id: "visitor_low_004",
      ip_address: "203.0.113.42",
      pages_visited: ["/"],
      time_on_site_seconds: 18,
      visit_count: 1,
      referral_source: "direct",
      device_type: "mobile",
    },
  },
];

interface ScenarioCardProps {
  scenario: Scenario;
  isActive: boolean;
  isDisabled: boolean;
  onRun: (scenario: Scenario) => void;
}

function ScenarioCard({
  scenario,
  isActive,
  isDisabled,
  onRun,
}: ScenarioCardProps): React.ReactElement {
  const pages = scenario.data.pages_visited ?? [];
  const minutes = Math.floor((scenario.data.time_on_site_seconds ?? 0) / 60);
  const seconds = (scenario.data.time_on_site_seconds ?? 0) % 60;
  const timeLabel =
    minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;

  return (
    <div
      className={`rounded-xl border p-5 flex flex-col gap-4 transition-all duration-300 ${
        isActive
          ? "border-accent/60 bg-accent/5 shadow-[0_0_24px_rgba(0,255,136,0.06)]"
          : "border-border bg-surface hover:border-border/80"
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span
              className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border"
              style={{
                color: scenario.tagColor,
                borderColor: `${scenario.tagColor}40`,
                backgroundColor: `${scenario.tagColor}12`,
              }}
            >
              {scenario.tag}
            </span>
          </div>
          <h3 className="font-display font-bold text-white text-sm">{scenario.label}</h3>
          <p className="text-muted text-xs font-mono mt-0.5 leading-relaxed">
            {scenario.description}
          </p>
        </div>
      </div>

      {/* Signal metadata */}
      <div className="grid grid-cols-3 gap-2 text-[10px] font-mono">
        <div className="rounded-lg bg-background px-2.5 py-2">
          <div className="text-muted mb-0.5">Pages</div>
          <div className="text-white font-semibold">{pages.length}</div>
        </div>
        <div className="rounded-lg bg-background px-2.5 py-2">
          <div className="text-muted mb-0.5">Time</div>
          <div className="text-white font-semibold">{timeLabel}</div>
        </div>
        <div className="rounded-lg bg-background px-2.5 py-2">
          <div className="text-muted mb-0.5">Visits</div>
          <div className="text-white font-semibold">{scenario.data.visit_count ?? 1}×</div>
        </div>
      </div>

      {/* Pages list */}
      <div className="flex flex-wrap gap-1">
        {pages.map((p) => (
          <span
            key={p}
            className="text-[9px] font-mono text-muted/70 bg-background border border-border rounded px-1.5 py-0.5"
          >
            {p}
          </span>
        ))}
      </div>

      {/* CTA */}
      <button
        onClick={() => onRun(scenario)}
        disabled={isDisabled}
        className={`w-full rounded-lg py-2 text-xs font-mono font-semibold transition-all ${
          isActive
            ? "bg-accent/20 text-accent border border-accent/40 cursor-default"
            : "bg-accent text-black hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed"
        }`}
      >
        {isActive ? "▶ Running…" : "Run Analysis →"}
      </button>
    </div>
  );
}

export default function VisitorScenarios(): React.ReactElement {
  const router = useRouter();
  const { submit, isSubmitting, isLoading, result, error, pipelineStep, pipelineProgress, reset } =
    useAccountAnalysis();

  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);
  const [completedAccountId, setCompletedAccountId] = useState<string | null>(null);

  const isPipelineRunning = isLoading && !isSubmitting;

  // Capture result when pipeline completes
  useEffect(() => {
    if (result && activeScenarioId) {
      setCompletedAccountId(result.account_id);
    }
  }, [result, activeScenarioId]);

  const handleRun = async (scenario: Scenario): Promise<void> => {
    if (isSubmitting || isPipelineRunning) return;
    reset();
    setActiveScenarioId(scenario.id);
    setCompletedAccountId(null);
    await submit(scenario.data);
  };

  const handleReset = (): void => {
    reset();
    setActiveScenarioId(null);
    setCompletedAccountId(null);
  };

  return (
    <div className="space-y-6">
      {/* Section header */}
      <div>
        <h2 className="font-display font-bold text-xl text-white mb-1">Visitor Signal Scenarios</h2>
        <p className="text-muted text-sm font-mono max-w-2xl">
          Click any scenario to trigger a real backend analysis. Each scenario represents a
          different visitor intent profile — the AI pipeline will identify the company, score
          intent, and generate a sales playbook.
        </p>
      </div>

      {/* Pipeline progress (shown while running) */}
      {isPipelineRunning && (
        <div className="space-y-3">
          <PipelineProgress
            step={pipelineStep}
            progress={pipelineProgress}
            companyName={
              SCENARIOS.find((s) => s.id === activeScenarioId)?.label ?? "Visitor Signal"
            }
          />
          <button
            onClick={handleReset}
            className="text-xs font-mono text-muted hover:text-white transition-colors"
          >
            ← Cancel and reset
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

      {/* Scenario grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SCENARIOS.map((scenario) => (
          <ScenarioCard
            key={scenario.id}
            scenario={scenario}
            isActive={activeScenarioId === scenario.id && (isSubmitting || isPipelineRunning)}
            isDisabled={isSubmitting || isPipelineRunning}
            onRun={handleRun}
          />
        ))}
      </div>

      {/* Completed — navigate to results */}
      {completedAccountId && !isPipelineRunning && !isSubmitting && !error && (
        <div className="rounded-lg border border-accent/30 bg-accent/5 p-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-accent text-sm font-mono font-semibold">Analysis complete</p>
            <p className="text-muted text-xs font-mono mt-0.5">
              Intelligence report is ready. Open it or run another scenario.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleReset}
              className="text-muted text-xs font-mono hover:text-white transition-colors"
            >
              Run another →
            </button>
            <button
              onClick={() => router.push(`/account/${completedAccountId}`)}
              className="rounded-lg bg-accent text-black text-xs font-mono font-semibold px-4 py-2 hover:bg-accent/90 transition-colors"
            >
              View report →
            </button>
          </div>
        </div>
      )}

      {/* Signal legend */}
      <div className="border-t border-border pt-6">
        <p className="text-[10px] font-mono text-muted mb-3 uppercase tracking-widest">
          Signal reference
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {SCENARIOS.map((s) => (
            <div key={s.id} className="flex items-center gap-2">
              <span
                className="h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: s.tagColor }}
              />
              <span className="text-xs font-mono text-muted">{s.signal}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
