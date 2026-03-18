import json
import logging
from typing import ClassVar, Optional

from backend.agents.base_agent import BaseAgent
from backend.core.llm_service import generate_json
from backend.domain.base import BaseEntity
from backend.domain.company import CompanyProfile
from backend.domain.intelligence import AccountIntelligence

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are a senior sales intelligence analyst writing an executive briefing for a sales team.

Given comprehensive account intelligence data, write a concise 3-5 sentence executive summary that is:
1. ACTIONABLE — tell the salesperson what to do, not just what you found
2. SPECIFIC — reference actual data points (company name, signals, tech stack, leader names)
3. URGENT — convey why NOW is the right time to engage
4. CONFIDENT — state findings with appropriate certainty

## Writing Guidelines:
- Sentence 1: Company overview (who they are, size, industry)
- Sentence 2: Key business signals or growth indicators
- Sentence 3: Visitor intent/persona insights (if available)
- Sentence 4: Tech stack fit or competitive angle
- Sentence 5: Recommended next step with specific contact if known

## Response Format (STRICT JSON):
{
  "ai_summary": "string — 3-5 sentence executive briefing",
  "confidence_score": 0.0 to 1.0,
  "reasoning": "string — explain how you weighted different intelligence sources"
}
"""


def _build_summary_prompt(intel: AccountIntelligence) -> str:
    """Build the full prompt with all intelligence data for summary generation."""
    intel_data: dict = {
        "company": {
            "name": intel.company.company_name,
            "domain": intel.company.domain,
            "industry": intel.company.industry,
            "size": intel.company.company_size_estimate,
            "headquarters": intel.company.headquarters,
            "description": intel.company.description,
            "revenue_range": intel.company.annual_revenue_range,
        },
    }

    if intel.persona:
        intel_data["persona"] = {
            "role": intel.persona.likely_role,
            "department": intel.persona.department,
            "seniority": intel.persona.seniority_level.value,
            "confidence": intel.persona.confidence_score,
            "signals": intel.persona.behavioral_signals[:4],
        }

    if intel.intent:
        intel_data["intent"] = {
            "score": intel.intent.intent_score,
            "stage": intel.intent.intent_stage.value,
            "signals": intel.intent.signals_detected[:4],
        }

    if intel.tech_stack and intel.tech_stack.technologies:
        intel_data["tech_stack"] = [
            {"name": t.name, "category": t.category.value}
            for t in intel.tech_stack.technologies[:5]
        ]

    if intel.business_signals and intel.business_signals.signals:
        intel_data["signals"] = [
            {"type": s.signal_type.value, "title": s.title, "description": s.description}
            for s in intel.business_signals.signals[:4]
        ]

    if intel.leadership and intel.leadership.leaders:
        intel_data["leadership"] = [
            {"name": l.name, "title": l.title}
            for l in intel.leadership.leaders[:4]
        ]

    if intel.playbook:
        intel_data["playbook"] = {
            "priority": intel.playbook.priority.value,
            "action_count": len(intel.playbook.recommended_actions),
            "top_action": intel.playbook.recommended_actions[0].action if intel.playbook.recommended_actions else None,
        }

    return f"""{SUMMARY_SYSTEM_PROMPT}

## Full Account Intelligence:
```json
{json.dumps(intel_data, indent=2)}
```

Write a compelling executive briefing that a sales rep can read in 30 seconds and know exactly what to do next."""


class _SummaryLLMResponse(BaseEntity):
    """Schema for validating LLM summary output."""

    ai_summary: str = ""
    confidence_score: float = 0.0
    reasoning: str = ""


def _mock_summary(intel: AccountIntelligence) -> str:
    """Rule-based fallback summary when LLM is unavailable."""
    c = intel.company
    parts: list[str] = []

    size = c.company_size_estimate or "unknown-size"
    hq = c.headquarters or "an undisclosed location"
    parts.append(f"{c.company_name} is a {size} {c.industry or 'company'} based in {hq}.")

    if intel.business_signals and intel.business_signals.signals:
        signal_titles = [s.title for s in intel.business_signals.signals[:2]]
        parts.append(f"Recent activity includes: {' and '.join(signal_titles)}, suggesting growth momentum.")

    if intel.intent:
        stage = intel.intent.intent_stage.value
        score = intel.intent.intent_score
        parts.append(
            f"A site visitor scored {score}/10 intent (stage: {stage}), "
            f"indicating {'active evaluation' if score >= 7 else 'early-stage interest'}."
        )

    if intel.persona:
        parts.append(
            f"The visitor is likely a {intel.persona.likely_role} "
            f"({intel.persona.seniority_level.value.replace('_', ' ').title()}) "
            f"in {intel.persona.department or 'an unidentified department'}."
        )

    if intel.playbook:
        priority = intel.playbook.priority.value
        action_count = len(intel.playbook.recommended_actions)
        parts.append(f"Recommend {priority}-priority outreach with {action_count} targeted actions.")

    return " ".join(parts)


def _compute_confidence(intel: AccountIntelligence) -> float:
    """Weighted average of sub-agent confidence scores."""
    weights = [
        (intel.company.confidence_score, 0.25),
        (intel.intent.confidence_score if intel.intent else 0.0, 0.20),
        (intel.persona.confidence_score if intel.persona else 0.0, 0.15),
        (intel.tech_stack.confidence_score if intel.tech_stack else 0.0, 0.10),
        (intel.business_signals.confidence_score if intel.business_signals else 0.0, 0.10),
        (intel.leadership.confidence_score if intel.leadership else 0.0, 0.10),
        (intel.playbook.confidence_score if intel.playbook else 0.0, 0.10),
    ]
    return sum(score * weight for score, weight in weights)


class SummaryAgent(BaseAgent):
    """Generates AI narrative summary and assembles final AccountIntelligence using LLM."""

    agent_name: ClassVar[str] = "summary_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        return isinstance(input, AccountIntelligence)

    async def run(self, input: BaseEntity) -> AccountIntelligence:
        if not self.validate_input(input):
            return AccountIntelligence(
                company=CompanyProfile(company_name="Unknown"),
                ai_summary="Analysis failed — insufficient data.",
                confidence_score=0.0,
                reasoning_trace=["Summary agent received invalid input"],
            )

        intel: AccountIntelligence = input  # type: ignore[assignment]

        company_lower = intel.company.company_name.strip().lower()
        if company_lower in ("unknown", "unknown (private ip)", "none", ""):
            logger.info("Unknown company — generating uncertainty-aware summary")
            intent_info = ""
            if intel.intent:
                intent_info = f" The visitor showed {intel.intent.intent_stage.value.lower()}-stage intent with a score of {intel.intent.intent_score}/10."
            persona_info = ""
            if intel.persona:
                persona_info = f" Behavioral signals suggest a {intel.persona.likely_role} ({intel.persona.seniority_level.value.replace('_', ' ').title()}) persona with {round(intel.persona.confidence_score * 100)}% confidence."

            summary_text = (
                f"The visitor's company could not be identified from their IP address.{intent_info}{persona_info} "
                f"Recommend capturing company information through direct engagement (chat, form, or gated content) "
                f"before investing in outbound sales actions."
            )
            confidence = _compute_confidence(intel)
            merged_trace = list(intel.reasoning_trace) + ["Summary: Unknown company — uncertainty-aware summary generated"]
            return AccountIntelligence(
                id=intel.id,
                company=intel.company,
                persona=intel.persona,
                intent=intel.intent,
                tech_stack=intel.tech_stack,
                business_signals=intel.business_signals,
                leadership=intel.leadership,
                playbook=intel.playbook,
                ai_summary=summary_text,
                analyzed_at=intel.analyzed_at,
                confidence_score=round(max(0.0, min(1.0, confidence)), 2),
                reasoning_trace=merged_trace,
            )

        logger.info("Generating AI summary via LLM for %s", intel.company.company_name)
        summary_text: Optional[str] = None
        llm_confidence: Optional[float] = None

        async with self._timed_call("llm_summary_generation"):
            prompt = _build_summary_prompt(intel)
            llm_result = await generate_json(
                prompt=prompt,
                response_model=_SummaryLLMResponse,
                temperature=0.3,
                max_tokens=2048,
            )

        if llm_result and llm_result.ai_summary:
            summary_text = llm_result.ai_summary
            llm_confidence = llm_result.confidence_score
            reasoning_entry = f"[LLM] {llm_result.reasoning or 'AI-generated executive briefing'}"
            logger.info("LLM summary generated successfully (confidence=%.2f)", llm_confidence)
        else:
            logger.warning("LLM summary generation failed — falling back to template logic")
            summary_text = _mock_summary(intel)
            reasoning_entry = "[MOCK FALLBACK] Template-based summary generation"

        confidence = llm_confidence if llm_confidence is not None else _compute_confidence(intel)

        merged_trace = list(intel.reasoning_trace) + [reasoning_entry]

        return AccountIntelligence(
            id=intel.id,
            company=intel.company,
            persona=intel.persona,
            intent=intel.intent,
            tech_stack=intel.tech_stack,
            business_signals=intel.business_signals,
            leadership=intel.leadership,
            playbook=intel.playbook,
            ai_summary=summary_text,
            analyzed_at=intel.analyzed_at,
            confidence_score=round(max(0.0, min(1.0, confidence)), 2),
            reasoning_trace=merged_trace,
        )
