// Auto-sync with backend/api/schemas/responses.py and backend/domain/

export type JobStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export type IntentStage = "AWARENESS" | "CONSIDERATION" | "EVALUATION" | "PURCHASE";

export type SeniorityLevel =
  | "C_LEVEL"
  | "VP"
  | "DIRECTOR"
  | "MANAGER"
  | "INDIVIDUAL_CONTRIBUTOR"
  | "UNKNOWN";

export type TechCategory =
  | "CRM"
  | "MARKETING_AUTOMATION"
  | "ANALYTICS"
  | "WEBSITE_PLATFORM"
  | "CLOUD_INFRASTRUCTURE"
  | "COMMUNICATION"
  | "OTHER";

export type SignalType =
  | "HIRING"
  | "FUNDING"
  | "EXPANSION"
  | "PRODUCT_LAUNCH"
  | "PARTNERSHIP"
  | "LEADERSHIP_CHANGE"
  | "OTHER";

export type Priority = "HIGH" | "MEDIUM" | "LOW";

// ── Request bodies ───────────────────────────────────────────────────────────

export interface VisitorAnalysisRequest {
  visitor_id: string;
  ip_address: string;
  pages_visited?: string[];
  time_on_site_seconds?: number;
  visit_count?: number;
  referral_source?: string;
  device_type?: string;
}

export interface CompanyAnalysisRequest {
  company_name: string;
  domain?: string;
}

// ── Response schemas ─────────────────────────────────────────────────────────

export interface AnalysisAcceptedResponse {
  success: boolean;
  job_id: string;
  status: string;
  poll_url: string;
}

export interface JobStatusResponse {
  success: boolean;
  job_id: string;
  status: JobStatus;
  progress: number;
  current_step: string | null;
  result_id: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface TechnologySchema {
  name: string;
  category: TechCategory;
  confidence_score: number;
}

export interface LeaderSchema {
  name: string;
  title: string;
  department: string | null;
  linkedin_url: string | null;
}

export interface SignalSchema {
  signal_type: SignalType;
  title: string;
  description: string;
  source_url: string | null;
}

export interface RecommendedActionSchema {
  action: string;
  rationale: string;
  priority: Priority;
}

export interface AccountIntelligenceResponse {
  success: boolean;
  account_id: string;
  company_name: string;
  domain: string | null;
  industry: string | null;
  company_size: string | null;
  headquarters: string | null;
  description: string | null;
  annual_revenue_range: string | null;
  intent_score: number | null;
  intent_stage: IntentStage | null;
  likely_role: string | null;
  seniority_level: SeniorityLevel | null;
  persona_confidence: number | null;
  technologies: TechnologySchema[];
  business_signals: SignalSchema[];
  leaders: LeaderSchema[];
  recommended_actions: RecommendedActionSchema[];
  talking_points: string[];
  outreach_template: string | null;
  playbook_priority: Priority | null;
  ai_summary: string;
  analyzed_at: string;
  confidence_score: number;
}

export interface AccountSummary {
  success: boolean;
  account_id: string;
  company_name: string;
  domain: string | null;
  industry: string | null;
  intent_score: number | null;
  confidence_score: number;
  analyzed_at: string;
}

export interface AccountListResponse {
  success: boolean;
  accounts: AccountSummary[];
  total: number;
  page: number;
  page_size: number;
}
