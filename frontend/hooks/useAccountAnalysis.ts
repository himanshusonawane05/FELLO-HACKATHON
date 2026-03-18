"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useJobPoller } from "./useJobPoller";
import type {
  AccountIntelligenceResponse,
  CompanyAnalysisRequest,
  VisitorAnalysisRequest,
} from "@/types/intelligence";

export interface UseAccountAnalysisReturn {
  submit: (data: VisitorAnalysisRequest | CompanyAnalysisRequest) => Promise<void>;
  result: AccountIntelligenceResponse | null;
  isSubmitting: boolean;
  isLoading: boolean;
  error: string | null;
  pipelineStep: string | null;
  pipelineProgress: number;
  reset: () => void;
}

function isVisitorRequest(
  data: VisitorAnalysisRequest | CompanyAnalysisRequest
): data is VisitorAnalysisRequest {
  return "visitor_id" in data;
}

export function useAccountAnalysis(preloadAccountId?: string): UseAccountAnalysisReturn {
  const [jobId, setJobId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<AccountIntelligenceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(!!preloadAccountId);
  const [error, setError] = useState<string | null>(null);

  const { jobStatus } = useJobPoller(jobId);

  // Pre-load account by ID (used on account detail page)
  useEffect(() => {
    if (!preloadAccountId) return;
    setIsLoading(true);
    api
      .getAccount(preloadAccountId)
      .then((data) => setResult(data))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load account"))
      .finally(() => setIsLoading(false));
  }, [preloadAccountId]);

  // React to job completion
  useEffect(() => {
    if (!jobStatus) return;

    if (jobStatus.status === "COMPLETED" && jobStatus.result_id) {
      api
        .getAccount(jobStatus.result_id)
        .then((data) => {
          setResult(data);
          setJobId(null);
        })
        .catch((err) =>
          setError(err instanceof Error ? err.message : "Failed to fetch result")
        );
    } else if (jobStatus.status === "FAILED") {
      setError(jobStatus.error ?? "Analysis failed");
      setJobId(null);
    }
  }, [jobStatus]);

  const submit = useCallback(
    async (data: VisitorAnalysisRequest | CompanyAnalysisRequest): Promise<void> => {
      setIsSubmitting(true);
      setError(null);
      setResult(null);
      try {
        const response = isVisitorRequest(data)
          ? await api.analyzeVisitor(data)
          : await api.analyzeCompany(data);
        setJobId(response.job_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Submission failed");
      } finally {
        setIsSubmitting(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setJobId(null);
    setResult(null);
    setError(null);
    setIsLoading(false);
    setIsSubmitting(false);
  }, []);

  const isActiveJob = !!jobId && jobStatus?.status !== "COMPLETED" && jobStatus?.status !== "FAILED";

  return {
    submit,
    result,
    isSubmitting,
    isLoading: isLoading || isActiveJob,
    error,
    pipelineStep: jobStatus?.current_step ?? null,
    pipelineProgress: jobStatus?.progress ?? 0,
    reset,
  };
}
