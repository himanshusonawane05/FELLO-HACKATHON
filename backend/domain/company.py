from typing import Optional

from pydantic import Field

from backend.domain.base import BaseEntity


class CompanyInput(BaseEntity):
    """Minimal company input for direct enrichment."""

    company_name: str
    domain: Optional[str] = None


class CompanyProfile(BaseEntity):
    """Enriched company information from multiple data sources."""

    company_name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    company_size_estimate: Optional[str] = None
    headquarters: Optional[str] = None
    founding_year: Optional[int] = None
    description: Optional[str] = None
    annual_revenue_range: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
