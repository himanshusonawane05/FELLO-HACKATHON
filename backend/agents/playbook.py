import json
import logging
from typing import ClassVar, Optional

from backend.agents.base_agent import BaseAgent
from backend.core.llm_service import generate_json
from backend.domain.base import BaseEntity
from backend.domain.intent import IntentStage
from backend.domain.persona import PersonaInference, SeniorityLevel
from backend.domain.playbook import Priority, RecommendedAction, SalesPlaybook

logger = logging.getLogger(__name__)

PLAYBOOK_SYSTEM_PROMPT = """You are a world-class B2B sales strategist. Given comprehensive account intelligence data, generate a prioritized, actionable sales playbook.

Your playbook must be specific to the company — reference real data points from the intelligence provided. Generic advice is worthless.

## Priority Determination:
- HIGH: intent_score >= 7.0 OR active buying signals (pricing visits, demo requests)
- MEDIUM: intent_score 4.0-6.9 OR consideration-stage signals
- LOW: intent_score < 4.0 OR awareness-stage only

## Response Format (STRICT JSON):
{
  "priority": "HIGH" | "MEDIUM" | "LOW",
  "recommended_actions": [
    {
      "action": "string — specific, actionable step",
      "rationale": "string — why this action matters, referencing intelligence data",
      "priority": "HIGH" | "MEDIUM" | "LOW"
    }
  ],
  "talking_points": ["string — specific conversation starters referencing discovered intelligence"],
  "outreach_template": "string — personalized outreach email/message template",
  "confidence_score": 0.0 to 1.0,
  "reasoning": "string — explain your strategic reasoning"
}

## Rules:
- Generate 3-5 recommended actions, ordered by priority
- Each action MUST reference specific intelligence data (company name, leader names, signals, tech stack)
- Talking points should be conversation starters, not generic statements
- Outreach template must be personalized with actual company/contact details
- Never fabricate data — only reference what is provided in the intelligence
"""


def _build_playbook_prompt(intel: "AccountIntelligence") -> str:
    """Build the full prompt with all intelligence data for playbook generation."""
    company_data = {
        "company_name": intel.company.company_name,
        "domain": intel.company.domain,
        "industry": intel.company.industry,
        "company_size": intel.company.company_size_estimate,
        "headquarters": intel.company.headquarters,
        "description": intel.company.description,
    }

    intel_data: dict = {"company": company_data}

    if intel.persona:
        intel_data["persona"] = {
            "likely_role": intel.persona.likely_role,
            "department": intel.persona.department,
            "seniority_level": intel.persona.seniority_level.value,
        }

    if intel.intent:
        intel_data["intent"] = {
            "intent_score": intel.intent.intent_score,
            "intent_stage": intel.intent.intent_stage.value,
            "signals_detected": intel.intent.signals_detected[:5],
        }

    if intel.tech_stack and intel.tech_stack.technologies:
        intel_data["tech_stack"] = [
            {"name": t.name, "category": t.category.value}
            for t in intel.tech_stack.technologies[:6]
        ]

    if intel.business_signals and intel.business_signals.signals:
        intel_data["business_signals"] = [
            {"type": s.signal_type.value, "title": s.title, "description": s.description}
            for s in intel.business_signals.signals[:4]
        ]

    if intel.leadership and intel.leadership.leaders:
        intel_data["leadership"] = [
            {"name": l.name, "title": l.title, "department": l.department}
            for l in intel.leadership.leaders[:5]
        ]

    return f"""{PLAYBOOK_SYSTEM_PROMPT}

## Account Intelligence Data:
```json
{json.dumps(intel_data, indent=2)}
```

Generate a comprehensive, data-driven sales playbook for this account. Every recommendation must reference specific data points from the intelligence above."""


class _PlaybookLLMResponse(BaseEntity):
    """Schema for validating LLM playbook output."""

    priority: str = "MEDIUM"
    recommended_actions: list[dict] = []
    talking_points: list[str] = []
    outreach_template: Optional[str] = None
    confidence_score: float = 0.0
    reasoning: str = ""


def _intent_to_priority(score: float) -> Priority:
    if score >= 7.0:
        return Priority.HIGH
    if score >= 4.0:
        return Priority.MEDIUM
    return Priority.LOW


def _mock_playbook(intel: "AccountIntelligence") -> SalesPlaybook:
    """Rule-based fallback when LLM is unavailable."""
    company = intel.company
    intent_score = intel.intent.intent_score if intel.intent else 5.0
    intent_stage = intel.intent.intent_stage if intel.intent else IntentStage.CONSIDERATION
    signals = intel.business_signals.signals if intel.business_signals else []
    leaders = intel.leadership.leaders if intel.leadership else []
    priority = _intent_to_priority(intent_score)

    actions: list[RecommendedAction] = []
    if leaders:
        target = next(
            (l for l in leaders if "sales" in l.title.lower() or "revenue" in l.title.lower()),
            leaders[0],
        )
        actions.append(RecommendedAction(
            action=f"Connect with {target.name} ({target.title}) on LinkedIn",
            rationale=f"Direct decision maker at {company.company_name}",
            priority=Priority.HIGH,
        ))

    if intent_stage in (IntentStage.EVALUATION, IntentStage.PURCHASE):
        actions.append(RecommendedAction(
            action="Schedule personalized product demo within 48 hours",
            rationale=f"Intent score {intent_score}/10 indicates active evaluation",
            priority=Priority.HIGH,
        ))

    talking_points = []
    if company.industry:
        talking_points.append(f"Lead with {company.industry} vertical success stories")

    contact_name = leaders[0].name.split()[0] if leaders else "there"
    signal_ref = signals[0].title if signals else f"{company.company_name}'s growth"
    outreach = (
        f"Hi {contact_name}, I noticed {company.company_name} is {signal_ref.lower()} — "
        f"we've helped similar {company.industry or 'companies'} increase qualified pipeline by 30-50%. "
        f"Would you be open to a quick 20-min call this week?"
    )

    reasoning = f"[MOCK FALLBACK] Priority {priority.value} based on intent {intent_score}/10"
    return SalesPlaybook(
        priority=priority,
        recommended_actions=actions,
        talking_points=talking_points,
        outreach_template=outreach,
        confidence_score=0.5,
        reasoning_trace=[reasoning],
    )


class PlaybookAgent(BaseAgent):
    """Synthesises a context-aware sales playbook using LLM reasoning."""

    agent_name: ClassVar[str] = "playbook_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        from backend.domain.intelligence import AccountIntelligence
        return isinstance(input, AccountIntelligence)

    async def run(self, input: BaseEntity) -> SalesPlaybook:
        from backend.domain.intelligence import AccountIntelligence

        if not self.validate_input(input):
            return SalesPlaybook(
                priority=Priority.LOW,
                confidence_score=0.0,
                reasoning_trace=["Insufficient data for playbook generation"],
            )

        intel: AccountIntelligence = input  # type: ignore[assignment]

        company_lower = intel.company.company_name.strip().lower()
        if company_lower in ("unknown", "unknown (private ip)", "none", ""):
            logger.info("Skipping playbook for unknown company")
            return SalesPlaybook(
                priority=Priority.LOW,
                recommended_actions=[
                    RecommendedAction(
                        action="Identify the visitor's company through follow-up engagement",
                        rationale="Visitor company could not be resolved from IP — direct identification needed before sales action",
                        priority=Priority.HIGH,
                    ),
                ],
                talking_points=["Company identity unknown — focus on qualification before outreach"],
                confidence_score=0.1,
                reasoning_trace=["Company is unknown — minimal playbook generated"],
            )

        logger.info("Generating playbook via LLM for %s", intel.company.company_name)

        async with self._timed_call("llm_playbook_generation"):
            prompt = _build_playbook_prompt(intel)
            llm_result = await generate_json(
                prompt=prompt,
                response_model=_PlaybookLLMResponse,
                temperature=0.3,
                max_tokens=4096,
            )

        if llm_result is None:
            logger.warning("LLM playbook generation failed — falling back to rule-based logic")
            return _mock_playbook(intel)

        logger.info("LLM playbook generated: priority=%s, actions=%d",
                     llm_result.priority, len(llm_result.recommended_actions))

        try:
            priority = Priority(llm_result.priority)
        except ValueError:
            priority = _intent_to_priority(
                intel.intent.intent_score if intel.intent else 5.0
            )

        actions: list[RecommendedAction] = []
        for a in llm_result.recommended_actions[:5]:
            try:
                action_priority = Priority(a.get("priority", "MEDIUM"))
            except (ValueError, AttributeError):
                action_priority = Priority.MEDIUM
            actions.append(RecommendedAction(
                action=a.get("action", "Review account intelligence"),
                rationale=a.get("rationale", "Based on collected intelligence"),
                priority=action_priority,
            ))

        reasoning_text = llm_result.reasoning or "LLM-generated sales playbook"
        return SalesPlaybook(
            priority=priority,
            recommended_actions=actions,
            talking_points=llm_result.talking_points or [],
            outreach_template=llm_result.outreach_template,
            confidence_score=max(0.0, min(1.0, llm_result.confidence_score)),
            reasoning_trace=[f"[LLM] {reasoning_text}"],
        )
