from enum import Enum
from typing import Optional

from pydantic import Field

from backend.domain.base import BaseEntity


class SignalType(str, Enum):
    HIRING = "HIRING"
    FUNDING = "FUNDING"
    EXPANSION = "EXPANSION"
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"
    PARTNERSHIP = "PARTNERSHIP"
    LEADERSHIP_CHANGE = "LEADERSHIP_CHANGE"
    OTHER = "OTHER"


class Signal(BaseEntity):
    """A single business signal indicating opportunity."""

    signal_type: SignalType = SignalType.OTHER
    title: str
    description: str
    source_url: Optional[str] = None
    detected_at: Optional[str] = None


class BusinessSignals(BaseEntity):
    """Collection of business signals for opportunity detection."""

    signals: list[Signal] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
