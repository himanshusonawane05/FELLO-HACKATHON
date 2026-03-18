from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VisitorAnalysisRequest(BaseModel):
    """Request body for POST /analyze/visitor — matches api-contracts.md §2.1."""

    visitor_id: str = Field(..., min_length=1, json_schema_extra={"example": "v-001"})
    ip_address: str = Field(..., min_length=1, json_schema_extra={"example": "34.201.114.42"})
    pages_visited: list[str] = Field(default_factory=list, min_length=1)
    time_on_site_seconds: int = Field(default=0, ge=0)
    visit_count: int = Field(default=1, ge=1)
    referral_source: Optional[str] = None
    device_type: Optional[str] = None
    location: Optional[str] = None
    timestamps: list[str] = Field(default_factory=list)


class CompanyAnalysisRequest(BaseModel):
    """Request body for POST /analyze/company — matches api-contracts.md §2.2."""

    company_name: str = Field(..., min_length=1, max_length=200)
    domain: Optional[str] = None


class BatchAnalysisRequest(BaseModel):
    """Request body for POST /analyze/batch — matches api-contracts.md §2.3."""

    companies: list[CompanyAnalysisRequest] = Field(..., min_length=1, max_length=20)
