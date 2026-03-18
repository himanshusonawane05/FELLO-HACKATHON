from typing import Optional

from pydantic import Field

from backend.domain.base import BaseEntity


class Leader(BaseEntity):
    """A discovered company leader / decision maker."""

    name: str
    title: str
    department: Optional[str] = None
    linkedin_url: Optional[str] = None
    source_url: Optional[str] = None


class LeadershipProfile(BaseEntity):
    """Key decision makers at the target company."""

    leaders: list[Leader] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
