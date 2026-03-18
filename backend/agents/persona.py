import json
import logging
from typing import ClassVar, Optional

from backend.agents.base_agent import BaseAgent
from backend.core.llm_service import generate_json
from backend.domain.base import BaseEntity
from backend.domain.persona import PersonaInference, SeniorityLevel
from backend.domain.visitor import VisitorSignal

logger = logging.getLogger(__name__)

PERSONA_SYSTEM_PROMPT = """You are an expert B2B sales intelligence analyst. Your task is to infer the most likely buyer persona from website visitor behavioral signals.

Analyze the visitor's page visit patterns, time on site, visit frequency, and referral source to determine:
1. Their most likely job role/title
2. Their department
3. Their seniority level
4. Key behavioral signals that led to your inference

## Seniority Level Values (use EXACTLY one of these):
- "C_LEVEL" — CEO, CTO, CFO, CMO, CRO
- "VP" — VP of Sales, VP Engineering, VP Marketing
- "DIRECTOR" — Director, Head of Department
- "MANAGER" — Manager, Team Lead
- "INDIVIDUAL_CONTRIBUTOR" — Engineer, Analyst, Specialist
- "UNKNOWN" — Cannot determine

## Behavioral Pattern Guidelines:
- /pricing, /plans, /enterprise → buyer/decision-maker evaluating cost
- /api, /docs, /developer, /sdk → technical evaluator
- /case-studies, /roi, /results → building business case
- /demo, /trial → high-intent evaluation
- /features, /product → product comparison
- /blog, /resources, /learn → awareness/research stage
- /about, /team, /leadership → partnership/BD interest
- Multiple visits (>2) → serious evaluation
- Long dwell time (>120s) → deep engagement

## Response Format (STRICT JSON):
{
  "likely_role": "string — specific job title like 'VP of Sales' or 'Senior Software Engineer'",
  "department": "string — e.g. 'Sales', 'Engineering', 'Marketing', 'Product'",
  "seniority_level": "string — one of: C_LEVEL, VP, DIRECTOR, MANAGER, INDIVIDUAL_CONTRIBUTOR, UNKNOWN",
  "behavioral_signals": ["string — list of observed behavioral signals with interpretation"],
  "confidence_score": 0.0 to 1.0,
  "reasoning": "string — explain your reasoning step by step"
}
"""


def _build_persona_prompt(signal: VisitorSignal) -> str:
    """Build the full prompt including visitor data for persona inference."""
    visitor_data = {
        "pages_visited": signal.pages_visited,
        "time_on_site_seconds": signal.time_on_site_seconds,
        "visit_count": signal.visit_count,
        "referral_source": signal.referral_source,
        "device_type": signal.device_type,
    }
    return f"""{PERSONA_SYSTEM_PROMPT}

## Visitor Data to Analyze:
```json
{json.dumps(visitor_data, indent=2)}
```

Analyze the visitor data above and respond with a single JSON object matching the response format. Be specific and actionable in your role inference."""


class _PersonaLLMResponse(BaseEntity):
    """Schema for validating LLM JSON output before mapping to PersonaInference."""

    likely_role: str
    department: Optional[str] = None
    seniority_level: str = "UNKNOWN"
    behavioral_signals: list[str] = []
    confidence_score: float = 0.0
    reasoning: str = ""


def _mock_persona(signal: VisitorSignal) -> PersonaInference:
    """Rule-based fallback when LLM is unavailable."""
    pages = " ".join(signal.pages_visited).lower()

    patterns = [
        (["pricing", "plans", "enterprise"], "VP of Sales", "Sales", SeniorityLevel.VP, 0.15),
        (["ai-sales", "ai-agent", "revenue"], "Head of Revenue Operations", "Revenue", SeniorityLevel.DIRECTOR, 0.12),
        (["case-studies", "roi", "results"], "Sales Operations Manager", "Sales", SeniorityLevel.MANAGER, 0.10),
        (["docs", "api", "developer", "sdk"], "Senior Software Engineer", "Engineering", SeniorityLevel.INDIVIDUAL_CONTRIBUTOR, 0.08),
        (["features", "product", "demo"], "Product Manager", "Product", SeniorityLevel.MANAGER, 0.08),
        (["about", "team", "leadership"], "Business Development Manager", "Business Development", SeniorityLevel.MANAGER, 0.05),
        (["blog", "resources", "learn"], "Marketing Specialist", "Marketing", SeniorityLevel.INDIVIDUAL_CONTRIBUTOR, 0.03),
    ]

    best_role, best_dept, best_seniority = "Business Stakeholder", "Business", SeniorityLevel.UNKNOWN
    confidence = 0.35

    for keywords, role, dept, seniority, boost in patterns:
        if any(kw in pages for kw in keywords):
            best_role, best_dept, best_seniority = role, dept, seniority
            confidence = min(0.35 + boost + (signal.visit_count * 0.05), 0.95)
            break

    reasoning = f"[MOCK FALLBACK] Page pattern ({', '.join(signal.pages_visited[:3])}) indicates {best_role}."
    return PersonaInference(
        likely_role=best_role,
        department=best_dept,
        seniority_level=best_seniority,
        behavioral_signals=["Fallback: rule-based pattern matching"],
        confidence_score=round(confidence, 2),
        reasoning=reasoning,
        reasoning_trace=[reasoning],
    )


class PersonaAgent(BaseAgent):
    """Infers visitor persona from page-visit behavioral patterns using LLM reasoning."""

    agent_name: ClassVar[str] = "persona_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        return isinstance(input, VisitorSignal)

    async def run(self, input: BaseEntity) -> PersonaInference:
        if not self.validate_input(input):
            return PersonaInference(
                likely_role="Unknown Visitor",
                seniority_level=SeniorityLevel.UNKNOWN,
                confidence_score=0.0,
                reasoning="No visitor signal provided",
            )

        signal: VisitorSignal = input  # type: ignore[assignment]
        logger.info("Calling Gemini for persona inference (pages=%s, visits=%d)",
                     signal.pages_visited[:3], signal.visit_count)

        async with self._timed_call("llm_persona_inference"):
            prompt = _build_persona_prompt(signal)
            llm_result = await generate_json(
                prompt=prompt,
                response_model=_PersonaLLMResponse,
                temperature=0.1,
                max_tokens=1024,
            )

        if llm_result is None:
            logger.warning("LLM persona inference failed — falling back to rule-based logic")
            return _mock_persona(signal)

        logger.info("LLM persona inference succeeded: role=%s, confidence=%.2f",
                     llm_result.likely_role, llm_result.confidence_score)

        try:
            seniority = SeniorityLevel(llm_result.seniority_level)
        except ValueError:
            seniority = SeniorityLevel.UNKNOWN

        reasoning_text = llm_result.reasoning or "LLM-inferred persona from behavioral signals"
        return PersonaInference(
            likely_role=llm_result.likely_role,
            department=llm_result.department,
            seniority_level=seniority,
            behavioral_signals=llm_result.behavioral_signals or ["LLM-analyzed behavioral patterns"],
            confidence_score=max(0.0, min(1.0, llm_result.confidence_score)),
            reasoning=reasoning_text,
            reasoning_trace=[f"[LLM] {reasoning_text}"],
        )
