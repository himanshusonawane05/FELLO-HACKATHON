from enum import Enum

from pydantic import Field

from backend.domain.base import BaseEntity


class TechCategory(str, Enum):
    CRM = "CRM"
    MARKETING_AUTOMATION = "MARKETING_AUTOMATION"
    ANALYTICS = "ANALYTICS"
    WEBSITE_PLATFORM = "WEBSITE_PLATFORM"
    CLOUD_INFRASTRUCTURE = "CLOUD_INFRASTRUCTURE"
    COMMUNICATION = "COMMUNICATION"
    OTHER = "OTHER"


class Technology(BaseEntity):
    """A single detected technology."""

    name: str
    category: TechCategory = TechCategory.OTHER
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)


class TechStack(BaseEntity):
    """Detected technology stack from website analysis."""

    technologies: list[Technology] = Field(default_factory=list)
    detection_method: str = "script_analysis"
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
