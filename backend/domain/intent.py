from enum import Enum

from pydantic import Field

from backend.domain.base import BaseEntity


class IntentStage(str, Enum):
    AWARENESS = "AWARENESS"
    CONSIDERATION = "CONSIDERATION"
    EVALUATION = "EVALUATION"
    PURCHASE = "PURCHASE"


class IntentScore(BaseEntity):
    """Buying intent assessment from visitor behavior signals."""

    intent_score: float = Field(ge=0.0, le=10.0, default=0.0)
    intent_stage: IntentStage = IntentStage.AWARENESS
    signals_detected: list[str] = Field(default_factory=list)
    page_score_breakdown: dict[str, float] = Field(default_factory=dict)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
