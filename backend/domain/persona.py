from enum import Enum
from typing import Optional

from pydantic import Field

from backend.domain.base import BaseEntity


class SeniorityLevel(str, Enum):
    C_LEVEL = "C_LEVEL"
    VP = "VP"
    DIRECTOR = "DIRECTOR"
    MANAGER = "MANAGER"
    INDIVIDUAL_CONTRIBUTOR = "INDIVIDUAL_CONTRIBUTOR"
    UNKNOWN = "UNKNOWN"


class PersonaInference(BaseEntity):
    """Inferred visitor persona from behavioral signals."""

    likely_role: str
    department: Optional[str] = None
    seniority_level: SeniorityLevel = SeniorityLevel.UNKNOWN
    behavioral_signals: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning: str = ""
    reasoning_trace: list[str] = Field(default_factory=list)
