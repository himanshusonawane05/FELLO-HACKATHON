from typing import Optional

from pydantic import Field

from backend.domain.base import BaseEntity


class VisitorSignal(BaseEntity):
    """Raw visitor activity data from website tracking."""

    visitor_id: str
    ip_address: str
    pages_visited: list[str] = Field(default_factory=list)
    time_on_site_seconds: int = Field(ge=0, default=0)
    visit_count: int = Field(ge=1, default=1)
    referral_source: Optional[str] = None
    device_type: Optional[str] = None
    location: Optional[str] = None
    timestamps: list[str] = Field(default_factory=list)
