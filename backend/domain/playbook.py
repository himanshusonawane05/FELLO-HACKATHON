from enum import Enum
from typing import Optional

from pydantic import Field

from backend.domain.base import BaseEntity


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendedAction(BaseEntity):
    """A single recommended sales action."""

    action: str
    rationale: str
    priority: Priority = Priority.MEDIUM


class SalesPlaybook(BaseEntity):
    """AI-generated sales strategy for the account."""

    priority: Priority = Priority.MEDIUM
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    outreach_template: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
