import operator
from typing import Annotated, Optional

from typing_extensions import TypedDict

from backend.domain.company import CompanyInput, CompanyProfile
from backend.domain.intelligence import AccountIntelligence
from backend.domain.intent import IntentScore
from backend.domain.leadership import LeadershipProfile
from backend.domain.persona import PersonaInference
from backend.domain.playbook import SalesPlaybook
from backend.domain.signals import BusinessSignals
from backend.domain.tech_stack import TechStack
from backend.domain.visitor import VisitorSignal


class PipelineState(TypedDict):
    """Shared state object passed through the LangGraph pipeline."""

    # Input — exactly one will be set per run
    visitor_signal: Optional[VisitorSignal]
    company_input: Optional[CompanyInput]

    # Stage 0 output
    identified_company: Optional[CompanyInput]

    # Stage 1 outputs (parallel: enrichment, intent, persona)
    company_profile: Optional[CompanyProfile]
    persona: Optional[PersonaInference]
    intent: Optional[IntentScore]

    # Stage 2 outputs (parallel: tech_stack, signals, leadership)
    tech_stack: Optional[TechStack]
    business_signals: Optional[BusinessSignals]
    leadership: Optional[LeadershipProfile]

    # Final outputs
    playbook: Optional[SalesPlaybook]
    intelligence: Optional[AccountIntelligence]

    # Metadata
    job_id: str
    errors: Annotated[list[str], operator.add]
    reasoning_trace: Annotated[list[str], operator.add]
