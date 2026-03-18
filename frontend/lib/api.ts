import type {
  AccountIntelligenceResponse,
  AccountListResponse,
  AccountSummary,
  AnalysisAcceptedResponse,
  CompanyAnalysisRequest,
  JobStatusResponse,
  VisitorAnalysisRequest,
} from "@/types/intelligence";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail?.error ?? body?.detail?.message ?? body?.error ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// Backend returns nested structure; frontend components expect flat shape.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformAccountResponse(raw: any): AccountIntelligenceResponse {
  return {
    success: true,
    account_id: raw.account_id,
    company_name: raw.company?.company_name ?? "Unknown",
    domain: raw.company?.domain ?? null,
    industry: raw.company?.industry ?? null,
    company_size: raw.company?.company_size_estimate ?? null,
    headquarters: raw.company?.headquarters ?? null,
    description: raw.company?.description ?? null,
    annual_revenue_range: raw.company?.annual_revenue_range ?? null,
    intent_score: raw.intent?.intent_score ?? null,
    intent_stage: raw.intent?.intent_stage ?? null,
    likely_role: raw.persona?.likely_role ?? null,
    seniority_level: raw.persona?.seniority_level ?? null,
    persona_confidence: raw.persona?.confidence_score ?? null,
    technologies: raw.tech_stack?.technologies ?? [],
    business_signals: raw.business_signals?.signals ?? [],
    leaders: raw.leadership?.leaders ?? [],
    recommended_actions: raw.playbook?.recommended_actions ?? [],
    talking_points: raw.playbook?.talking_points ?? [],
    outreach_template: raw.playbook?.outreach_template ?? null,
    playbook_priority: raw.playbook?.priority ?? null,
    ai_summary: raw.ai_summary ?? "",
    analyzed_at: raw.analyzed_at ?? new Date().toISOString(),
    confidence_score: raw.confidence_score ?? 0,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformJobStatus(raw: any): JobStatusResponse {
  return {
    success: true,
    job_id: raw.job_id,
    status: raw.status,
    progress: Math.round((raw.progress ?? 0) * 100),
    current_step: raw.current_step ?? null,
    result_id: raw.result_id ?? null,
    error: raw.error ?? null,
    created_at: raw.created_at ?? new Date().toISOString(),
    updated_at: raw.updated_at ?? new Date().toISOString(),
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformAccountList(raw: any): AccountListResponse {
  return {
    success: true,
    accounts: (raw.accounts ?? []).map(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (a: any): AccountSummary => ({
        success: true,
        account_id: a.account_id,
        company_name: a.company_name,
        domain: a.domain ?? null,
        industry: a.industry ?? null,
        intent_score: a.intent_score ?? null,
        confidence_score: a.confidence_score ?? 0,
        analyzed_at: a.analyzed_at ?? new Date().toISOString(),
      })
    ),
    total: raw.total ?? 0,
    page: raw.page ?? 1,
    page_size: raw.page_size ?? 20,
  };
}

export const api = {
  async analyzeVisitor(body: VisitorAnalysisRequest): Promise<AnalysisAcceptedResponse> {
    const raw = await request<Record<string, unknown>>("/analyze/visitor", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return {
      success: true,
      job_id: raw.job_id as string,
      status: (raw.status as string) ?? "PENDING",
      poll_url: (raw.poll_url as string) ?? `/jobs/${raw.job_id}`,
    };
  },

  async analyzeCompany(body: CompanyAnalysisRequest): Promise<AnalysisAcceptedResponse> {
    const raw = await request<Record<string, unknown>>("/analyze/company", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return {
      success: true,
      job_id: raw.job_id as string,
      status: (raw.status as string) ?? "PENDING",
      poll_url: (raw.poll_url as string) ?? `/jobs/${raw.job_id}`,
    };
  },

  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const raw = await request<Record<string, unknown>>(`/jobs/${jobId}`);
    return transformJobStatus(raw);
  },

  async getAccount(accountId: string): Promise<AccountIntelligenceResponse> {
    const raw = await request<Record<string, unknown>>(`/accounts/${accountId}`);
    return transformAccountResponse(raw);
  },

  async listAccounts(page = 1, pageSize = 20): Promise<AccountListResponse> {
    const raw = await request<Record<string, unknown>>(
      `/accounts?page=${page}&page_size=${pageSize}`
    );
    return transformAccountList(raw);
  },
};
