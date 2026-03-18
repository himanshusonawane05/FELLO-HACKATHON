import logging
from typing import ClassVar

from backend.agents.base_agent import BaseAgent
from backend.domain.base import BaseEntity
from backend.domain.intent import IntentScore, IntentStage
from backend.domain.visitor import VisitorSignal

logger = logging.getLogger(__name__)

# keyword → score contribution
_PAGE_SCORES: dict[str, float] = {
    "pricing": 3.0,
    "plans": 2.5,
    "demo": 2.5,
    "enterprise": 2.0,
    "ai-sales": 2.0,
    "case-studies": 2.0,
    "roi": 1.8,
    "features": 1.5,
    "product": 1.5,
    "integration": 1.2,
    "docs": 1.0,
    "api": 1.0,
    "about": 0.5,
    "blog": 0.4,
    "resources": 0.3,
}

_SIGNAL_LABELS: dict[str, str] = {
    "pricing": "Pricing page visit (high intent)",
    "demo": "Demo request (very high intent)",
    "enterprise": "Enterprise plans viewed (large deal signal)",
    "case-studies": "Case study consumption (late-stage evaluation)",
    "features": "Feature exploration (product comparison)",
    "ai-sales": "AI sales agent page (product fit evaluation)",
    "docs": "Documentation accessed (technical evaluation)",
    "blog": "Content consumption (awareness stage)",
}


def _score_to_stage(score: float) -> IntentStage:
    if score >= 8.0:
        return IntentStage.PURCHASE
    if score >= 6.0:
        return IntentStage.EVALUATION
    if score >= 3.5:
        return IntentStage.CONSIDERATION
    return IntentStage.AWARENESS


class IntentScorerAgent(BaseAgent):
    """Scores buying intent from page visits, visit count, and time on site (rule-based)."""

    agent_name: ClassVar[str] = "intent_scorer_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        return isinstance(input, VisitorSignal)

    async def run(self, input: BaseEntity) -> IntentScore:
        """VisitorSignal → IntentScore (rule-based scoring model)."""
        if not self.validate_input(input):
            return IntentScore(
                intent_score=0.0,
                intent_stage=IntentStage.AWARENESS,
                confidence_score=0.0,
                reasoning_trace=["No visitor signal"],
            )

        signal: VisitorSignal = input  # type: ignore[assignment]
        page_breakdown: dict[str, float] = {}
        signals_detected: list[str] = []
        base_score = 0.0

        for page in signal.pages_visited:
            page_lower = page.lower()
            for kw, pts in _PAGE_SCORES.items():
                if kw in page_lower:
                    page_breakdown[page] = pts
                    base_score += pts
                    if kw in _SIGNAL_LABELS:
                        label = _SIGNAL_LABELS[kw]
                        if label not in signals_detected:
                            signals_detected.append(label)
                    break
            else:
                page_breakdown[page] = 0.2
                base_score += 0.2

        # Bonuses
        visit_bonus = min(signal.visit_count * 0.4, 2.0)
        time_bonus = min(signal.time_on_site_seconds / 300.0, 1.5)

        if visit_bonus > 0:
            page_breakdown["repeat_visit_bonus"] = round(visit_bonus, 2)
            signals_detected.append(f"{signal.visit_count} visit(s) — repeat engagement")
        if time_bonus > 0.3:
            page_breakdown["time_on_site_bonus"] = round(time_bonus, 2)

        total = min(base_score + visit_bonus + time_bonus, 10.0)
        stage = _score_to_stage(total)
        confidence = min(0.5 + len(signal.pages_visited) * 0.05 + signal.visit_count * 0.03, 0.95)

        return IntentScore(
            intent_score=round(total, 1),
            intent_stage=stage,
            signals_detected=signals_detected or ["General website browsing"],
            page_score_breakdown={k: round(v, 2) for k, v in page_breakdown.items()},
            confidence_score=round(confidence, 2),
            reasoning_trace=[
                f"Base page score: {round(base_score, 2)} across {len(signal.pages_visited)} pages",
                f"Visit bonus: +{round(visit_bonus, 2)} (×{signal.visit_count} visits)",
                f"Time bonus: +{round(time_bonus, 2)} ({signal.time_on_site_seconds}s on site)",
                f"Final: {round(total, 1)}/10 → {stage.value}",
            ],
        )
