import logging
from typing import ClassVar, Optional

from backend.agents.base_agent import BaseAgent
from backend.core.llm_service import generate_json
from backend.domain.base import BaseEntity
from backend.domain.company import CompanyProfile
from backend.domain.tech_stack import TechCategory, TechStack, Technology

logger = logging.getLogger(__name__)


def _is_unknown_company(name: str) -> bool:
    lower = name.strip().lower()
    return lower in ("unknown", "unknown (private ip)", "none", "")


class _TechLLMResponse(BaseEntity):
    """Schema for LLM-inferred tech stack."""
    technologies: list[dict] = []
    confidence_score: float = 0.5


class TechStackAgent(BaseAgent):
    """Detects technology stack using LLM + company context.

    Returns empty stack for unknown/unresolved companies.
    """

    agent_name: ClassVar[str] = "tech_stack_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        return isinstance(input, CompanyProfile)

    async def run(self, input: BaseEntity) -> TechStack:
        if not self.validate_input(input):
            return TechStack(confidence_score=0.0, reasoning_trace=["No company profile"])

        company: CompanyProfile = input  # type: ignore[assignment]

        if _is_unknown_company(company.company_name):
            logger.info("[%s] unknown company — returning empty tech stack", self.agent_name)
            return TechStack(
                technologies=[],
                detection_method="skipped",
                confidence_score=0.0,
                reasoning_trace=["Company is unknown — tech stack detection skipped"],
            )

        if company.confidence_score < 0.3:
            logger.info("[%s] low confidence company — returning empty tech stack", self.agent_name)
            return TechStack(
                technologies=[],
                detection_method="skipped",
                confidence_score=0.0,
                reasoning_trace=["Company confidence too low for reliable tech stack detection"],
            )

        logger.info("[%s] inferring tech stack for %s via LLM", self.agent_name, company.company_name)

        prompt = f"""You are a technology analyst. Based on this company profile, infer their likely technology stack.

Company: {company.company_name}
Industry: {company.industry or 'Unknown'}
Domain: {company.domain or 'Unknown'}
Size: {company.company_size_estimate or 'Unknown'}
Description: {company.description or 'No description available'}

Return a JSON object with:
- technologies: array of objects, each with:
  - name: string (e.g. "Salesforce", "AWS")
  - category: string, one of: CRM, MARKETING_AUTOMATION, ANALYTICS, WEBSITE_PLATFORM, CLOUD_INFRASTRUCTURE, COMMUNICATION, OTHER
  - confidence_score: float 0.0-1.0
- confidence_score: float 0.0-1.0 (overall confidence in this tech stack)

Only include technologies you are reasonably confident about. Max 6 technologies.
Return ONLY valid JSON."""

        result = await generate_json(
            prompt=prompt,
            response_model=_TechLLMResponse,
            temperature=0.1,
            max_tokens=1024,
        )

        if result and result.technologies:
            technologies = []
            for t in result.technologies[:6]:
                try:
                    cat = TechCategory(t.get("category", "OTHER"))
                except ValueError:
                    cat = TechCategory.OTHER
                technologies.append(Technology(
                    name=t.get("name", "Unknown"),
                    category=cat,
                    confidence_score=t.get("confidence_score", 0.5),
                ))
            return TechStack(
                technologies=technologies,
                detection_method="llm_inference",
                confidence_score=max(0.0, min(1.0, result.confidence_score)),
                reasoning_trace=[f"LLM inferred {len(technologies)} technologies for {company.company_name}"],
            )

        logger.warning("[%s] LLM tech stack inference failed", self.agent_name)
        return TechStack(
            technologies=[],
            detection_method="failed",
            confidence_score=0.0,
            reasoning_trace=["Tech stack inference failed"],
        )
