"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { JobStatusResponse } from "@/types/intelligence";

const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 150;

interface UseJobPollerReturn {
  jobStatus: JobStatusResponse | null;
  isPolling: boolean;
  pollError: string | null;
}

export function useJobPoller(jobId: string | null): UseJobPollerReturn {
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [pollError, setPollError] = useState<string | null>(null);
  const pollCount = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = useCallback(() => {
    setIsPolling(false);
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    if (!jobId) return;
    pollCount.current += 1;

    if (pollCount.current > MAX_POLLS) {
      setPollError("Analysis is taking longer than expected.");
      stopPolling();
      return;
    }

    try {
      const status = await api.getJobStatus(jobId);
      setJobStatus(status);

      if (status.status === "COMPLETED" || status.status === "FAILED") {
        stopPolling();
        return;
      }
    } catch (err) {
      setPollError(err instanceof Error ? err.message : "Polling failed");
      stopPolling();
      return;
    }

    timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
  }, [jobId, stopPolling]);

  useEffect(() => {
    if (!jobId) return;
    pollCount.current = 0;
    setPollError(null);
    setIsPolling(true);
    poll();

    return () => {
      stopPolling();
    };
  }, [jobId, poll, stopPolling]);

  return { jobStatus, isPolling, pollError };
}
