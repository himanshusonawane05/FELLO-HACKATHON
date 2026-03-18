import logging
from typing import ClassVar, Optional

from backend.agents.base_agent import BaseAgent
from backend.core.llm_service import generate_json
from backend.domain.base import BaseEntity
from backend.domain.company import CompanyInput, CompanyProfile

logger = logging.getLogger(__name__)


def _is_unknown_company(name: str) -> bool:
    """Check if company name indicates an unresolved identification."""
    lower = name.strip().lower()
    return lower in ("unknown", "unknown (private ip)", "none", "")


class _EnrichmentLLMResponse(BaseEntity):
    """Schema for LLM-generated company enrichment."""
    industry: Optional[str] = None
    company_size_estimate: Optional[str] = None
    headquarters: Optional[str] = None
    founding_year: Optional[int] = None
    description: Optional[str] = None
    annual_revenue_range: Optional[str] = None
    confidence_score: float = 0.5


class EnrichmentAgent(BaseAgent):
    """Enriches a CompanyInput into a full CompanyProfile.

    Uses Tavily web search for real data and LLM for synthesis.
    For Unknown/unresolved companies, returns minimal low-confidence profiles.
    """

    agent_name: ClassVar[str] = "enrichment_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        return isinstance(input, CompanyInput) and bool(input.company_name)

    async def run(self, input: BaseEntity) -> CompanyProfile:
        if not self.validate_input(input):
            return CompanyProfile(company_name="Unknown", confidence_score=0.0)

        company: CompanyInput = input  # type: ignore[assignment]

        if _is_unknown_company(company.company_name):
            logger.info("[%s] company is Unknown — returning low-confidence profile", self.agent_name)
            return CompanyProfile(
                company_name=company.company_name,
                domain=company.domain,
                confidence_score=0.1,
                reasoning_trace=[
                    "Company could not be identified from visitor IP",
                    "No enrichment data available for unknown company",
                ],
            )

        logger.info("[%s] enriching %s via Tavily + LLM", self.agent_name, company.company_name)

        search_context = await self._tavily_enrich(company.company_name, company.domain)

        llm_profile = await self._llm_enrich(company.company_name, company.domain, search_context)

        if llm_profile:
            return CompanyProfile(
                company_name=company.company_name,
                domain=company.domain or llm_profile.get("domain"),
                industry=llm_profile.get("industry"),
                company_size_estimate=llm_profile.get("company_size_estimate"),
                headquarters=llm_profile.get("headquarters"),
                founding_year=llm_profile.get("founding_year"),
                description=llm_profile.get("description"),
                annual_revenue_range=llm_profile.get("annual_revenue_range"),
                confidence_score=llm_profile.get("confidence_score", 0.6),
                data_sources=["tavily_search", "llm_synthesis"] if search_context else ["llm_synthesis"],
                reasoning_trace=[
                    f"Enriched {company.company_name} via LLM with {'web search context' if search_context else 'general knowledge'}",
                ],
            )

        logger.warning("[%s] LLM enrichment failed — returning minimal profile", self.agent_name)
        return CompanyProfile(
            company_name=company.company_name,
            domain=company.domain,
            confidence_score=0.3,
            data_sources=["fallback"],
            reasoning_trace=["LLM enrichment failed; returning minimal profile"],
        )

    async def _tavily_enrich(self, company_name: str, domain: Optional[str]) -> Optional[str]:
        """Search Tavily for company information. Returns concatenated search snippets."""
        try:
            from backend.tools.web_search import WebSearchTool

            tool = WebSearchTool()
            query = f"{company_name} company overview industry employees revenue"
            if domain:
                query = f"site:{domain} OR {query}"

            result = await tool.call(query=query, max_results=5)
            if result is None or not result.get("results"):
                logger.info("[%s] Tavily returned no results for %s", self.agent_name, company_name)
                return None

            snippets = [
                f"[{r.get('title', '')}] {r.get('snippet', '')}"
                for r in result["results"]
                if r.get("snippet")
            ]
            context = "\n".join(snippets[:5])
            logger.info("[%s] Tavily returned %d results for %s", self.agent_name, len(snippets), company_name)
            return context if context.strip() else None

        except Exception as exc:
            logger.warning("[%s] Tavily search failed for %s: %s", self.agent_name, company_name, exc)
            return None

    async def _llm_enrich(
        self, company_name: str, domain: Optional[str], search_context: Optional[str]
    ) -> Optional[dict]:
        """Use LLM to synthesize a company profile from search results or general knowledge."""
        context_block = ""
        if search_context:
            context_block = f"""
Here is web search context about the company:
---
{search_context}
---
Use this information to fill in the profile accurately.
"""
        else:
            context_block = "No web search results are available. Use your general knowledge if you know this company. If you don't recognize the company, set confidence_score below 0.4."

        prompt = f"""You are a B2B sales intelligence analyst. Generate a company profile for "{company_name}"{f' (domain: {domain})' if domain else ''}.

{context_block}

Return a JSON object with these fields:
- industry: string (e.g. "Technology / SaaS", "Financial Services")
- company_size_estimate: string (e.g. "50-200 employees")
- headquarters: string (e.g. "San Francisco, CA, USA")
- founding_year: integer or null
- description: string (2-3 sentence company description)
- annual_revenue_range: string (e.g. "$10M-$50M") or null
- confidence_score: float 0.0-1.0 (how confident you are in this data)

IMPORTANT: Only include information you are confident about. Set confidence_score based on data quality.
If you don't know the company, set confidence_score below 0.3 and leave fields null.

Return ONLY valid JSON, no markdown, no explanation."""

        result = await generate_json(
            prompt=prompt,
            response_model=_EnrichmentLLMResponse,
            temperature=0.1,
            max_tokens=1024,
        )

        if result:
            return result.model_dump()
        return None
