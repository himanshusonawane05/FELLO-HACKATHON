"use client";

import { useState } from "react";
import type { CompanyAnalysisRequest, VisitorAnalysisRequest } from "@/types/intelligence";

type FormMode = "company" | "visitor";

const REFERRAL_OPTIONS = ["direct", "organic_search", "paid_search", "social", "email", "referral"];
const DEVICE_OPTIONS = ["desktop", "mobile", "tablet"];

interface AnalysisFormProps {
  onSubmit: (data: VisitorAnalysisRequest | CompanyAnalysisRequest) => Promise<void>;
  isSubmitting: boolean;
}

function InputLabel({ children }: { children: React.ReactNode }): React.ReactElement {
  return (
    <label className="block text-[10px] font-mono text-muted mb-1 uppercase tracking-wider">
      {children}
    </label>
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
  required,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
}): React.ReactElement {
  return (
    <input
      required={required}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-white placeholder-muted font-mono focus:outline-none focus:border-accent transition-colors"
    />
  );
}

export default function AnalysisForm({
  onSubmit,
  isSubmitting,
}: AnalysisFormProps): React.ReactElement {
  const [mode, setMode] = useState<FormMode>("company");

  // Company mode fields
  const [companyName, setCompanyName] = useState("");
  const [domain, setDomain] = useState("");

  // Visitor mode fields
  const [visitorId, setVisitorId] = useState("");
  const [ipAddress, setIpAddress] = useState("");
  const [pagesInput, setPagesInput] = useState("");
  const [timeOnSite, setTimeOnSite] = useState(120);
  const [visitCount, setVisitCount] = useState(1);
  const [referralSource, setReferralSource] = useState("direct");
  const [deviceType, setDeviceType] = useState("desktop");

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (mode === "company") {
      await onSubmit({
        company_name: companyName,
        domain: domain || undefined,
      });
    } else {
      await onSubmit({
        visitor_id: visitorId || `visitor_${Date.now()}`,
        ip_address: ipAddress || "203.0.113.42",
        pages_visited: pagesInput
          .split(",")
          .map((p) => p.trim())
          .filter(Boolean),
        time_on_site_seconds: timeOnSite,
        visit_count: visitCount,
        referral_source: referralSource,
        device_type: deviceType,
      });
    }
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  };

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="analysis-form"
      className="rounded-xl border border-border bg-surface p-6 space-y-5"
    >
      {/* Mode tabs */}
      <div className="flex gap-2 items-center">
        {(["company", "visitor"] as FormMode[]).map((m) => (
          <button
            key={m}
            type="button"
            data-testid={`mode-${m}`}
            onClick={() => setMode(m)}
            className={`px-4 py-1.5 rounded-md text-sm font-mono transition-all ${
              mode === m
                ? "bg-accent text-black font-semibold"
                : "bg-background text-muted border border-border hover:border-accent"
            }`}
          >
            {m === "company" ? "Company Lookup" : "Visitor Signal"}
          </button>
        ))}
        <span className="ml-auto text-[10px] font-mono text-muted">
          {mode === "company" ? "Try: Salesforce, HubSpot, Stripe" : "Simulates a web visitor"}
        </span>
      </div>

      {mode === "company" ? (
        // ── Company mode ─────────────────────────────────────────────────────
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <InputLabel>Company name *</InputLabel>
            <input
              required
              data-testid="company-name-input"
              placeholder="e.g. Salesforce"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-white placeholder-muted font-mono focus:outline-none focus:border-accent transition-colors"
            />
          </div>
          <div>
            <InputLabel>Domain (optional)</InputLabel>
            <TextInput
              placeholder="e.g. salesforce.com"
              value={domain}
              onChange={setDomain}
            />
          </div>
        </div>
      ) : (
        // ── Visitor mode with scenario builder ───────────────────────────────
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <InputLabel>Visitor ID</InputLabel>
            <input
              data-testid="visitor-id-input"
              placeholder="visitor_abc123 (auto-generated)"
              value={visitorId}
              onChange={(e) => setVisitorId(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-white placeholder-muted font-mono focus:outline-none focus:border-accent transition-colors"
            />
            </div>
            <div>
              <InputLabel>IP Address</InputLabel>
              <TextInput
                placeholder="203.0.113.42 (default used)"
                value={ipAddress}
                onChange={setIpAddress}
              />
            </div>
          </div>

          <div>
            <InputLabel>Pages visited (comma-separated)</InputLabel>
            <TextInput
              placeholder="/pricing, /enterprise, /case-studies, /demo"
              value={pagesInput}
              onChange={setPagesInput}
            />
          </div>

          {/* Scenario sliders */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
            {/* Time on site */}
            <div>
              <InputLabel>
                Time on site —{" "}
                <span className="text-white">{formatTime(timeOnSite)}</span>
              </InputLabel>
              <input
                type="range"
                data-testid="time-on-site-slider"
                min={10}
                max={600}
                step={10}
                value={timeOnSite}
                onChange={(e) => setTimeOnSite(Number(e.target.value))}
                className="w-full h-1.5 rounded-full appearance-none bg-border cursor-pointer accent-accent"
              />
              <div className="flex justify-between text-[9px] font-mono text-muted mt-1">
                <span>10s</span>
                <span>10m</span>
              </div>
            </div>

            {/* Visit count */}
            <div>
              <InputLabel>
                Visit count —{" "}
                <span className="text-white">{visitCount}x</span>
              </InputLabel>
              <input
                type="range"
                data-testid="visit-count-slider"
                min={1}
                max={20}
                step={1}
                value={visitCount}
                onChange={(e) => setVisitCount(Number(e.target.value))}
                className="w-full h-1.5 rounded-full appearance-none bg-border cursor-pointer accent-accent"
              />
              <div className="flex justify-between text-[9px] font-mono text-muted mt-1">
                <span>1</span>
                <span>20</span>
              </div>
            </div>

            {/* Device type */}
            <div>
              <InputLabel>Device type</InputLabel>
              <div className="flex gap-1.5">
                {DEVICE_OPTIONS.map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDeviceType(d)}
                    className={`flex-1 py-1.5 rounded-md text-[10px] font-mono transition-all ${
                      deviceType === d
                        ? "bg-accent/20 text-accent border border-accent/40"
                        : "bg-background text-muted border border-border hover:border-accent/40"
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Referral source */}
          <div>
            <InputLabel>Referral source</InputLabel>
            <div className="flex flex-wrap gap-1.5">
              {REFERRAL_OPTIONS.map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setReferralSource(r)}
                  className={`px-3 py-1 rounded-md text-[10px] font-mono transition-all ${
                    referralSource === r
                      ? "bg-accent/20 text-accent border border-accent/40"
                      : "bg-background text-muted border border-border hover:border-accent/40"
                  }`}
                >
                  {r.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Submit */}
      <div className="flex items-center gap-4 pt-1">
        <button
          type="submit"
          data-testid="submit-btn"
          disabled={isSubmitting}
          className="rounded-lg bg-accent text-black font-display font-bold px-6 py-2.5 text-sm hover:bg-accent-dim transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? "Starting analysis…" : "Analyze →"}
        </button>
        {mode === "company" && companyName === "" && (
          <span className="text-[10px] font-mono text-muted">
            Quick start: type &quot;Salesforce&quot; above
          </span>
        )}
      </div>
    </form>
  );
}
