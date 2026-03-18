"""API response schemas — single source of truth is docs/api-contracts.md.

All schemas here MUST mirror the JSON structures defined in that document exactly.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Shared / primitives ────────────────────────────────────────────────────────

class AnalysisAcceptedResponse(BaseModel):
    """202 response for POST /analyze/visitor and /analyze/company."""

    job_id: str
    status: str = "PENDING"
    analysis_type: str
    message: str
    poll_url: str
    created_at: str


class BatchAcceptedResponse(BaseModel):
    """202 response for POST /analyze/batch."""

    batch_id: str
    job_ids: list[str]
    status: str = "PENDING"
    analysis_type: str = "batch"
    message: str
    poll_url: str
    created_at: str
    total: int


class JobStatusResponse(BaseModel):
    """200 response for GET /jobs/{job_id}."""

    job_id: str
    status: str
    progress: float = Field(ge=0.0, le=1.0)
    current_step: Optional[str] = None
    result_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class HealthResponse(BaseModel):
    """200 response for GET /health."""

    status: str = "ok"
    version: str = "1.0.0"


# ── Nested sub-schemas (mirrors domain models) ─────────────────────────────────

class CompanyProfileResponse(BaseModel):
    company_name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    company_size_estimate: Optional[str] = None
    headquarters: Optional[str] = None
    founding_year: Optional[int] = None
    description: Optional[str] = None
    annual_revenue_range: Optional[str] = None
    confidence_score: float
    data_sources: list[str] = Field(default_factory=list)


class PersonaInferenceResponse(BaseModel):
    likely_role: str
    department: Optional[str] = None
    seniority_level: str
    behavioral_signals: list[str] = Field(default_factory=list)
    confidence_score: float
    reasoning: str = ""


class IntentScoreResponse(BaseModel):
    intent_score: float
    intent_stage: str
    signals_detected: list[str] = Field(default_factory=list)
    page_score_breakdown: dict[str, float] = Field(default_factory=dict)
    confidence_score: float


class TechnologyResponse(BaseModel):
    name: str
    category: str
    confidence_score: float


class TechStackResponse(BaseModel):
    technologies: list[TechnologyResponse] = Field(default_factory=list)
    detection_method: str
    confidence_score: float


class SignalResponse(BaseModel):
    signal_type: str
    title: str
    description: str
    source_url: Optional[str] = None


class BusinessSignalsResponse(BaseModel):
    signals: list[SignalResponse] = Field(default_factory=list)
    confidence_score: float


class LeaderResponse(BaseModel):
    name: str
    title: str
    department: Optional[str] = None
    linkedin_url: Optional[str] = None
    source_url: Optional[str] = None


class LeadershipProfileResponse(BaseModel):
    leaders: list[LeaderResponse] = Field(default_factory=list)
    confidence_score: float


class RecommendedActionResponse(BaseModel):
    action: str
    rationale: str
    priority: str


class SalesPlaybookResponse(BaseModel):
    priority: str
    recommended_actions: list[RecommendedActionResponse] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    outreach_template: Optional[str] = None


# ── Top-level account response ─────────────────────────────────────────────────

class AccountIntelligenceResponse(BaseModel):
    """Full account intelligence — GET /accounts/{account_id}."""

    account_id: str
    company: CompanyProfileResponse
    persona: Optional[PersonaInferenceResponse] = None
    intent: Optional[IntentScoreResponse] = None
    tech_stack: Optional[TechStackResponse] = None
    business_signals: Optional[BusinessSignalsResponse] = None
    leadership: Optional[LeadershipProfileResponse] = None
    playbook: Optional[SalesPlaybookResponse] = None
    ai_summary: str = ""
    analyzed_at: str
    confidence_score: float
    reasoning_trace: list[str] = Field(default_factory=list)


class AccountSummaryResponse(BaseModel):
    """Compact account summary for GET /accounts list."""

    account_id: str
    company_name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    intent_score: Optional[float] = None
    confidence_score: float
    analyzed_at: str


class AccountListResponse(BaseModel):
    """Paginated list response for GET /accounts."""

    accounts: list[AccountSummaryResponse]
    total: int
    page: int
    page_size: int
