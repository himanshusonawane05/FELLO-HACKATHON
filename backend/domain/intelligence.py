from datetime import datetime
from typing import Optional

from pydantic import Field

from backend.domain.base import BaseEntity
from backend.domain.company import CompanyProfile
from backend.domain.intent import IntentScore
from backend.domain.leadership import LeadershipProfile
from backend.domain.persona import PersonaInference
from backend.domain.playbook import SalesPlaybook
from backend.domain.signals import BusinessSignals
from backend.domain.tech_stack import TechStack


class AccountIntelligence(BaseEntity):
    """Complete AI-generated account intelligence — the final output."""

    company: CompanyProfile
    persona: Optional[PersonaInference] = None
    intent: Optional[IntentScore] = None
    tech_stack: Optional[TechStack] = None
    business_signals: Optional[BusinessSignals] = None
    leadership: Optional[LeadershipProfile] = None
    playbook: Optional[SalesPlaybook] = None
    ai_summary: str = ""
    analyzed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
